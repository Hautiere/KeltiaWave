import { Routes } from '@angular/router';

import { AccueilComponent } from './pages/accueil/accueil.component';
import { EnregistrementComponent } from './pages/enregistrement/enregistrement.component';
import { ValidationComponent } from './pages/validation/validation.component';
import { EnregistrementsComponent } from './pages/enregistrements/enregistrements.component';
import { AdminComponent } from './pages/admin/admin.component';
import { UploaderComponent } from './pages/uploader/uploader.component'; // <= si tu l’as créé
import { EcrireComponent } from './pages/ecrire/ecrire.component';
import { LoginComponent } from './pages/login/login.component';
import { ValidateursComponent } from './pages/validateurs/validateurs.component';
import { V2AccountComponent } from './pages-v2/account/v2-account.component';
import { V2AdminComponent } from './pages-v2/admin/v2-admin.component';
import { V2AudioHomeComponent } from './pages-v2/audio-home/v2-audio-home.component';
import { V2EvaluateComponent } from './pages-v2/evaluate/v2-evaluate.component';
import { V2MyClassComponent } from './pages-v2/my-class/v2-my-class.component';
import { V2RecordComponent } from './pages-v2/record/v2-record.component';
import { V2WriteComponent } from './pages-v2/write/v2-write.component';

const redirectToPortal = () => {
  window.location.replace('/portal/index.html');
  return false;
};

export const routes: Routes = [
  { path: 'portal', canActivate: [redirectToPortal], children: [] },
  { path: '', component: V2AudioHomeComponent, pathMatch: 'full' },
  { path: 'home-bibliotheque', redirectTo: '', pathMatch: 'full' },
  { path: 'lire', component: V2RecordComponent },
  { path: 'enregistrer', redirectTo: 'lire', pathMatch: 'full' },
  { path: 'evaluer', component: V2EvaluateComponent },
  { path: 'ecrire', component: V2WriteComponent },
  { path: 'ma-classe', component: V2MyClassComponent },
  { path: 'admin', component: V2AdminComponent },
  { path: 'compte', component: V2AccountComponent },
  { path: 'login', redirectTo: 'compte' },
  { path: 'profil', redirectTo: 'compte' },

  { path: 'legacy', component: AccueilComponent, pathMatch: 'full' },
  { path: 'legacy/enregistrement', component: EnregistrementComponent },
  { path: 'legacy/ecrire', component: EcrireComponent },
  { path: 'legacy/uploader', component: UploaderComponent },
  { path: 'legacy/validation', component: ValidationComponent },
  { path: 'legacy/enregistrements', component: EnregistrementsComponent },
  { path: 'legacy/compte', component: LoginComponent },
  { path: 'legacy/validateurs', component: ValidateursComponent },
  { path: 'legacy/admin', component: AdminComponent },

  { path: 'v2', redirectTo: '', pathMatch: 'full' },
  { path: 'v2/lire', redirectTo: 'lire', pathMatch: 'full' },
  { path: 'v2/enregistrer', redirectTo: 'lire', pathMatch: 'full' },
  { path: 'v2/evaluer', redirectTo: 'evaluer', pathMatch: 'full' },
  { path: 'v2/ecrire', redirectTo: 'ecrire', pathMatch: 'full' },
  { path: 'v2/ma-classe', redirectTo: 'ma-classe', pathMatch: 'full' },
  { path: 'v2/admin', redirectTo: 'admin', pathMatch: 'full' },
  { path: 'v2/compte', redirectTo: 'compte', pathMatch: 'full' },
  { path: '**', redirectTo: '' }
];
