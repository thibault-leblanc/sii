import os
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INFRA_FILE = os.path.join(BASE_DIR, 'infrastructure.json')
SCHEMA_FILE = os.path.join(BASE_DIR, 'schema.json')

class RequestHandler(BaseHTTPRequestHandler):
    
    # Masquer les logs de requêtes pour garder un terminal propre
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            try:
                with open(os.path.join(BASE_DIR, 'templates', 'index.html'), 'rb') as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.wfile.write(b"<h1>Erreur</h1><p>Le fichier templates/index.html est introuvable.</p>")
        
        elif path == '/api/data/infrastructure.json':
            self.send_file(INFRA_FILE)
        elif path == '/api/data/schema.json':
            self.send_file(SCHEMA_FILE)
        elif path.startswith('/api/provisioning/'):
            node_id = urllib.parse.unquote(path.split('/')[-1])
            self.handle_provisioning(node_id)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/sauvegarder':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            filename = self.headers.get('X-File-Target')
            if filename not in ['infrastructure.json', 'schema.json']:
                self.send_response(403)
                self.end_headers()
                return
            
            filepath = INFRA_FILE if filename == 'infrastructure.json' else SCHEMA_FILE
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.send_json({"status": "success"})
        else:
            self.send_response(404)
            self.end_headers()

    def send_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.send_json(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def handle_provisioning(self, node_id):
        try:
            with open(INFRA_FILE, 'r', encoding='utf-8') as f:
                infra = json.load(f)
        except FileNotFoundError:
            self.send_json({"error": "infrastructure.json introuvable"}, 404)
            return

        if node_id not in infra.get('ressources_physiques', {}):
            self.send_json({"error": "Provisioning géré uniquement pour les ressources physiques."}, 400)
            return
            
        node = infra['ressources_physiques'][node_id]
        reseaux_globaux = infra.get('reseaux_globaux', {})
        
        # --- 1. CHECKLIST D'IMPACT ---
        checklist = "--- ACTIONS REQUISES SUR L'INFRASTRUCTURE ---\n\n"
        has_actions = False
        for iface_name, iface in node.get('interfaces', {}).items():
            if 'liaison_physique' in iface:
                try:
                    equipement, port = iface['liaison_physique'].split('/')
                    checklist += f"[ ] Sur '{equipement}' : Configurer le {port} en mode '{iface.get('mode', 'access')}'.\n"
                    if iface.get('mode') == 'trunk' and 'vlans_autorises' in iface:
                        checklist += f"    -> VLANs autorisés : {', '.join(iface['vlans_autorises'])}.\n"
                    elif 'vlan_id' in iface:
                        checklist += f"    -> Assigner au {iface['vlan_id']}.\n"
                    has_actions = True
                except ValueError:
                    pass
        if not has_actions:
            checklist += "✓ Aucune dépendance réseau physique documentée.\n"

        # --- 2. CALCUL DU NETPLAN ET DE L'ARBORESCENCE ---
        if "ubuntu" in node.get("systeme_exploitation", "").lower():
            netplan_eth = ""
            netplan_vlans = ""
            has_vlans = False

            for iface_name, iface in node.get('interfaces', {}).items():
                ip_cidr = iface.get('ip', '')
                gateway = ""
                
                # Déduction automatique du masque et de la passerelle
                if iface.get('vlan_id') and iface['vlan_id'] in reseaux_globaux:
                    res_global = reseaux_globaux[iface['vlan_id']]
                    if ip_cidr and '/' not in ip_cidr:
                        mask = res_global.get('sous_reseau', '').split('/')[1] if '/' in res_global.get('sous_reseau', '') else '24'
                        ip_cidr = f"{ip_cidr}/{mask}"
                    gateway = res_global.get('passerelle', '')

                if iface.get('type') == 'virtuelle' and iface.get('vlan_id'):
                    has_vlans = True
                    parent_iface = iface_name.split('.')[0]
                    vlan_num = ''.join(filter(str.isdigit, iface['vlan_id']))
                    netplan_vlans += f"    {iface_name}:\n      id: {vlan_num}\n      link: {parent_iface}\n      dhcp4: false\n"
                    if ip_cidr: netplan_vlans += f"      addresses: [{ip_cidr}]\n"
                else:
                    netplan_eth += f"    {iface_name}:\n      dhcp4: false\n"
                    if ip_cidr: netplan_eth += f"      addresses: [{ip_cidr}]\n"
                    if gateway: netplan_eth += f"      routes:\n        - to: default\n          via: {gateway}\n"

            netplan_yaml = "network:\n  version: 2\n  ethernets:\n" + netplan_eth
            if has_vlans:
                netplan_yaml += "  vlans:\n" + netplan_vlans

            # Préparation des commandes de création de dossiers
            mkdir_cmds = ""
            for nom, chemin in node.get("arborescence_hote", {}).items():
                mkdir_cmds += f"mkdir -p {chemin}\n"

            # --- 3. INJECTION DANS LE TEMPLATE ---
            template_path = os.path.join(BASE_DIR, 'templates', 'provisioning', 'ubuntu_init.template.sh')
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    script_bash = f.read()
                
                # Remplacement basique des balises
                script_bash = script_bash.replace('{{NODE_ID}}', node_id)
                script_bash = script_bash.replace('{{NETPLAN_YAML}}', netplan_yaml)
                script_bash = script_bash.replace('{{MKDIR_CMDS}}', mkdir_cmds)
            except FileNotFoundError:
                script_bash = f"echo 'Erreur : Fichier modèle introuvable : {template_path}'"
            
        else:
            script_bash = f"echo 'Type ou OS non supporté pour la génération automatique de {node_id}.'"

        self.send_json({"script": script_bash, "checklist": checklist})

if __name__ == '__main__':
    port = 5000
    server = HTTPServer(('127.0.0.1', port), RequestHandler)
    print("=====================================================")
    print(f"[*] Serveur IaaC local démarré sur http://127.0.0.1:{port}")
    print("=====================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Arrêt du serveur.")
        server.server_close()
