#!/bin/bash
# ==========================================
# AUTO-PROVISIONING POUR : {{NODE_ID}}
# PLATEFORME SII - CONFIGURATION INITIALE
# ==========================================

# 1. Configuration du Hostname
echo "[1/4] Définition du hostname local..."
hostnamectl set-hostname {{NODE_ID}}

# 2. Configuration Réseau (Netplan)
echo "[2/4] Création et application du fichier Netplan..."
cat <<EOF > /etc/netplan/99-{{NODE_ID}}-netplan.yaml
{{NETPLAN_YAML}}EOF

# Application de la configuration
netplan apply

# 3. Préparation de l'arborescence Docker/Projets
echo "[3/4] Création des répertoires de données..."
{{MKDIR_CMDS}}
# 4. Actions Finales
echo "[4/4] Opération terminée. Un redémarrage est conseillé."