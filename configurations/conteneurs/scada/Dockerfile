# SCADA de la plateforme : FUXA (IHM web), client OPC-UA de l'automate.
# Version figée (audit R4) : 1.3.3 est la version avec laquelle le projet a été réalisé et validé
# (instance de développement du poste d'administration, configurations/conteneurs/scada-dev).
FROM frangoteam/fuxa:1.3.3

USER root
WORKDIR /usr/src/app/FUXA/server

# Pilotes industriels utilisés par le projet, versions figées (mêmes que l'instance de développement).
RUN npm install modbus-serial@8.0.19 node-opcua@2.149.0 --no-audit --no-fund && \
    chown -R node:node /usr/src/app/FUXA

# Utilisateur node (uid 1000) : il doit pouvoir écrire dans le volume de données de l'hôte (~/scada/appdata).
USER node
EXPOSE 1881
CMD ["node", "main.js"]
