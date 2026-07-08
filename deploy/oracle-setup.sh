#!/usr/bin/env bash
# Alsamos LLM — Oracle Cloud (Ubuntu / Oracle Linux) avtomatik sozlash skripti
# Ishlatish:  sudo bash deploy/oracle-setup.sh
set -euo pipefail

log(){ printf "\n\033[1;36m\342\206\222 %s\033[0m\n" "$*"; }
ok(){ printf "\033[1;32m\342\234\223 %s\033[0m\n" "$*"; }
warn(){ printf "\033[1;33m\342\232\240 %s\033[0m\n" "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Iltimos sudo bilan ishga tushiring:  sudo bash deploy/oracle-setup.sh"
  exit 1
fi

# Repo ildizi (skript deploy/ ichida joylashgan)
cd "$(dirname "$0")/.."
REPO_DIR="$(pwd)"
log "Repo joylashuvi: $REPO_DIR"

# --- 1. Docker + paketlar ---
log "Docker va zarur paketlar o'rnatilmoqda..."
PKG=unknown
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg git iptables openssl
  command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh
  apt-get install -y docker-compose-plugin || true
  PKG=apt
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y git curl openssl
  command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh
  dnf install -y docker-compose-plugin || true
  PKG=dnf
else
  warn "Noma'lum distributiv — Docker'ni qo'lda o'rnating."
fi
systemctl enable --now docker || true
ok "Docker: $(docker --version 2>/dev/null || echo 'topilmadi')"

# --- 2. Ichki firewall: 80 va 443 portlarini ochish ---
log "Server ichki firewall'ida 80/443 ochilmoqda..."
if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
  firewall-cmd --permanent --add-port=80/tcp
  firewall-cmd --permanent --add-port=443/tcp
  firewall-cmd --reload
  ok "firewalld: 80/443 ochildi"
fi
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  ok "ufw: 80/443 ochildi"
fi
# Ubuntu OCI image'larida default iptables REJECT bo'ladi — ACCEPT qo'shamiz
if command -v iptables >/dev/null 2>&1; then
  iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 80 -j ACCEPT
  iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 443 -j ACCEPT
  if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save || true
  elif [ "$PKG" = "apt" ]; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent || true
    netfilter-persistent save || true
  else
    mkdir -p /etc/iptables && iptables-save > /etc/iptables/rules.v4 || true
  fi
  ok "iptables: 80/443 ACCEPT qo'shildi va saqlandi"
fi

# --- 3. .env tayyorlash ---
if [ ! -f backend/.env ]; then
  log "backend/.env yaratilmoqda..."
  cp backend/.env.production.example backend/.env
  SECRET="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  sed -i "s|^ALSAMOS_SECRET_KEY=.*|ALSAMOS_SECRET_KEY=${SECRET}|" backend/.env
  warn "backend/.env yaratildi. Endi OPENROUTER_API_KEY va (tavsiya) ALSAMOS_ACCESS_PASSWORD ni to'ldiring:"
  warn "    nano backend/.env"
else
  ok "backend/.env allaqachon mavjud — tegilmadi"
fi

# --- 4. Stack'ni ko'tarish ---
log "Docker stack qurilmoqda va ishga tushmoqda (app + Caddy)..."
log "Birinchi qurish bir necha daqiqa olishi mumkin (React build + Python)."
docker compose up -d --build

ok "Konteynerlar holati:"
docker compose ps || true

IP="$(curl -s ifconfig.me 2>/dev/null || echo '<SERVER_IP>')"
cat <<MSG

============================================================
 KEYINGI 3 QADAM (bularsiz sayt ochilmaydi!)
============================================================
1) OCI Console (brauzer) -> Networking -> Virtual Cloud Networks
   -> VCN -> Security Lists -> Default Security List
   -> Add Ingress Rules:
        Source 0.0.0.0/0   IP Protocol TCP   Dest port 80
        Source 0.0.0.0/0   IP Protocol TCP   Dest port 443
   (Buni VM ichidan emas, Oracle panelidan qilasiz.)

2) DNS (domen provayderingizda):
        ai.alsamos.com   A   ->   ${IP}

3) backend/.env to'ldirilganini tekshiring, so'ng:
        nano backend/.env
        docker compose up -d --build

Bir-ikki daqiqadan so'ng oching:  https://ai.alsamos.com
(Caddy avtomatik ravishda SSL sertifikat oladi.)

Foydali buyruqlar:
   Loglar:      docker compose logs -f
   Qayta ishga: docker compose up -d --build
   To'xtatish:  docker compose down
============================================================
MSG
