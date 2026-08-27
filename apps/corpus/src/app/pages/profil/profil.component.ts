import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { I18nService } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import {
  LEVEL_OPTIONS,
  ProfileService,
  ROLE_OPTIONS,
  SessionProfile,
} from '../../core/profile.service';

@Component({
  selector: 'app-profil',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './profil.component.html',
  styleUrls: ['./profil.component.scss']
})
export class ProfilComponent {
  readonly roles = ROLE_OPTIONS;
  readonly levels = LEVEL_OPTIONS;

  saved = false;

  constructor(
    readonly profileService: ProfileService,
    private readonly i18n: I18nService,
  ) {}

  get profile(): SessionProfile {
    return this.profileService.profile();
  }

  get weight(): number {
    return this.profileService.validationWeight();
  }

  get roleLabel(): string {
    return this.roleLabelFor(this.profile.role);
  }

  update(key: keyof SessionProfile, value: string): void {
    this.profileService.update({ [key]: value } as Partial<SessionProfile>);
    this.saved = true;
    setTimeout(() => this.saved = false, 1200);
  }

  reset(): void {
    this.profileService.reset();
  }

  roleLabelFor(role: string): string {
    return this.i18n.translate(`profile.role.${role}`);
  }

  roleDescriptionFor(role: string): string {
    return this.i18n.translate(`profile.roleDesc.${role}`);
  }

}
