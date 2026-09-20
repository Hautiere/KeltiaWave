import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize, timeout } from 'rxjs';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main>
      <h1>Choisir un nouveau mot de passe</h1>
      <ng-container *ngIf="!done; else success">
        <p>Définissez le nouveau mot de passe du compte qui a reçu cet email.</p>
        <form *ngIf="token; else missing" #form="ngForm" (ngSubmit)="submit()">
          <label for="new-password">Nouveau mot de passe</label>
          <input id="new-password" name="password" [(ngModel)]="password" [type]="visible ? 'text' : 'password'" autocomplete="new-password" required minlength="8" maxlength="128" [disabled]="busy">
          <small>Au moins 8 caractères.</small>
          <label for="confirm-password">Confirmer le nouveau mot de passe</label>
          <input id="confirm-password" name="confirmation" [(ngModel)]="confirmation" [type]="visible ? 'text' : 'password'" autocomplete="new-password" required maxlength="128" [disabled]="busy">
          <label class="visibility"><input type="checkbox" name="visible" [(ngModel)]="visible"> Afficher les mots de passe</label>
          <p class="error" role="alert" *ngIf="error">{{ error }}</p>
          <button type="submit" [disabled]="busy || form.invalid">{{ busy ? 'Enregistrement…' : 'Enregistrer mon nouveau mot de passe' }}</button>
        </form>
        <ng-template #missing><p class="error" role="alert">Le lien est incomplet. Ouvrez le lien reçu par email ou demandez-en un nouveau.</p></ng-template>
        <a routerLink="/compte" [queryParams]="{auth: 'forgot'}">Recevoir un nouveau lien</a>
      </ng-container>
      <ng-template #success>
        <p role="status">Votre mot de passe a été changé. Connectez-vous avec votre nouveau mot de passe.</p>
        <a routerLink="/compte">Revenir à la connexion</a>
      </ng-template>
    </main>
  `,
  styles: [`
    :host { display:block; padding:32px 16px; }
    main { max-width:540px; margin:0 auto; padding:28px; border:1px solid #dce4f3; border-radius:16px; background:white; color:#142344; }
    h1 { font-size:26px; margin:0 0 16px; } p { line-height:1.5; }
    form { display:flex; flex-direction:column; gap:10px; margin:24px 0; }
    label { font-weight:600; } input:not([type=checkbox]) { width:100%; box-sizing:border-box; padding:12px; border:1px solid #b8c9e8; border-radius:8px; font:inherit; }
    small { margin-bottom:8px; } .visibility { display:flex; gap:8px; align-items:center; margin:8px 0; font-weight:400; }
    button { padding:12px 16px; border:0; border-radius:8px; color:white; background:#245ff5; font:inherit; cursor:pointer; }
    button:disabled { opacity:.6; cursor:default; } a { color:#245ff5; } .error { color:#b42318; }
  `],
})
export class ResetPasswordComponent {
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);
  token = new URLSearchParams(inject(ActivatedRoute).snapshot.fragment || '').get('token') || '';
  password = '';
  confirmation = '';
  visible = false;
  busy = false;
  done = false;
  error = '';

  submit(): void {
    if (this.busy || !this.token) return;
    this.error = '';
    if (this.password.length < 8 || this.password.length > 128) {
      this.error = 'Le mot de passe doit contenir entre 8 et 128 caractères.';
      return;
    }
    if (this.password !== this.confirmation) {
      this.error = 'Les deux mots de passe ne correspondent pas.';
      return;
    }
    this.busy = true;
    this.auth.resetPassword(this.token, this.password).pipe(
      timeout(15000),
      finalize(() => { this.busy = false; this.cdr.markForCheck(); }),
    ).subscribe({
      next: () => {
        this.auth.logout();
        this.password = this.confirmation = this.token = '';
        window.history.replaceState(window.history.state, '', window.location.pathname);
        this.done = true;
      },
      error: (err) => {
        this.error = err.status === 400 || err.status === 422
          ? 'Ce lien est invalide, expiré ou déjà utilisé. Demandez un nouveau lien.'
          : 'Impossible de confirmer le changement. Réessayez ou demandez un nouveau lien.';
      },
    });
  }
}
