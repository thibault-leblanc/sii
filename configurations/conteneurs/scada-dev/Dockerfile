FROM frangoteam/fuxa:latest

# 1. Passer en root pour installer et corriger les permissions
USER root

# 2. Se placer dans le bon répertoire
WORKDIR /usr/src/app/FUXA/server

# 3. Installer les dépendances industrielles
RUN npm install modbus-serial@8.0.19 node-opcua@2.149.0 --no-audit --no-fund

# 4. RECORRECTION DES DROITS (Étape manquante)
# On s'assure que l'utilisateur 'node' réorganise et possède tout le dossier FUXA
RUN chown -R node:node /usr/src/app/FUXA

# 5. Repasser en utilisateur sécurisé
USER node

EXPOSE 1881

CMD ["node", "main.js"]
