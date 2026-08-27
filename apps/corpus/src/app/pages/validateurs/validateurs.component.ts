import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '../../core/translate.pipe';

interface ValidatorProfile {
  name: string;
  roleKey: string;
  origin: string;
  levelKey: string;
  focusKey: string;
  initials: string;
  tone: 'blue' | 'green' | 'yellow' | 'red' | 'slate';
}

@Component({
  selector: 'app-validateurs',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe],
  templateUrl: './validateurs.component.html',
  styleUrls: ['./validateurs.component.scss'],
})
export class ValidateursComponent {
  readonly nativeSpeakers: ValidatorProfile[] = [
    {
      name: 'Monique Hautiere',
      roleKey: 'validators.role.native',
      origin: 'Loguivy-Plougras',
      levelKey: 'validators.level.native',
      focusKey: 'validators.focus.native',
      initials: 'MH',
      tone: 'slate',
    },
    {
      name: 'Locuteur natif Tregor',
      roleKey: 'validators.role.native',
      origin: 'Tregor',
      levelKey: 'validators.level.native',
      focusKey: 'validators.focus.accent',
      initials: 'LT',
      tone: 'blue',
    },
    {
      name: 'Locutrice native Leon',
      roleKey: 'validators.role.native',
      origin: 'Leon',
      levelKey: 'validators.level.native',
      focusKey: 'validators.focus.pronunciation',
      initials: 'LL',
      tone: 'green',
    },
    {
      name: 'Locuteur natif Kerne',
      roleKey: 'validators.role.native',
      origin: 'Cornouaille',
      levelKey: 'validators.level.native',
      focusKey: 'validators.focus.domain',
      initials: 'LK',
      tone: 'yellow',
    },
  ];

  readonly teachers: ValidatorProfile[] = [
    {
      name: 'Professeur Kerne',
      roleKey: 'validators.role.teacher',
      origin: 'Cornouaille',
      levelKey: 'validators.level.teacher',
      focusKey: 'validators.focus.written',
      initials: 'PK',
      tone: 'blue',
    },
    {
      name: 'Professeure Leon',
      roleKey: 'validators.role.teacher',
      origin: 'Leon',
      levelKey: 'validators.level.teacher',
      focusKey: 'validators.focus.accent',
      initials: 'PL',
      tone: 'green',
    },
    {
      name: 'Professeur Treger',
      roleKey: 'validators.role.teacher',
      origin: 'Tregor',
      levelKey: 'validators.level.teacher',
      focusKey: 'validators.focus.pronunciation',
      initials: 'PT',
      tone: 'yellow',
    },
    {
      name: 'Professeure Gwened',
      roleKey: 'validators.role.teacher',
      origin: 'Vannetais',
      levelKey: 'validators.level.teacher',
      focusKey: 'validators.focus.domain',
      initials: 'PG',
      tone: 'red',
    },
  ];
}
