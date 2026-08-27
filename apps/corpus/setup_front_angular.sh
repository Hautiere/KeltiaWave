#!/bin/bash
set -e

mkdir -p src/app/pages/accueil
mkdir -p src/app/pages/enregistrement
mkdir -p src/app/pages/validation
mkdir -p src/app/pages/profil
mkdir -p src/app/pages/admin
mkdir -p src/app/core
mkdir -p src/app/shared

cat <<EOF > src/app/core/api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  getPhrases(): Observable<any[]> {
    return this.http.get<any[]>(\`\${this.baseUrl}/phrases/\`);
  }

  addPhrase(data: any): Observable<any> {
    return this.http.post(\`\${this.baseUrl}/phrases/\`, data);
  }
}
EOF

cat <<EOF > src/app/core/constants.ts
export const API_BASE_URL = '/api';
EOF

for page in accueil enregistrement validation profil admin
do
  component_name="$(echo ${page:0:1} | tr '[:lower:]' '[:upper:]')${page:1}"

  cat <<EOF > src/app/pages/$page/$page.component.ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-$page',
  templateUrl: './$page.component.html'
})
export class ${component_name}Component {}
EOF

  cat <<EOF > src/app/pages/$page/$page.component.html
<h2>${component_name}</h2>
<p>À compléter...</p>
EOF
done

cat <<EOF > README.md
# Corpus Breton - Frontend Angular

## Lancement local

1. Installer les dépendances :
   npm install
2. Lancer le serveur de dev :
   ng serve
3. Accéder à l'app :
   http://localhost:4200

## Structure du projet

- \`src/app/pages\` : une page par fonctionnalité principale
- \`src/app/core\` : services, constantes, gestion API
- \`src/app/shared\` : composants UI réutilisables

## À connecter au backend (FastAPI) via le service \`ApiService\`
EOF

echo "🎉 Structure Angular générée ! N'oublie pas d'ajouter les déclarations de composants à ton app.module.ts et les routes à app-routing.module.ts."
