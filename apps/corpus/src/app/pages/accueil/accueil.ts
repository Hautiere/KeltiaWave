import { Component, OnInit } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'app-accueil',
  standalone: true,
  templateUrl: './accueil.html',
  imports: [NgFor, NgIf, RouterLink],
})
export class AccueilComponent implements OnInit {
  phrases: any[] = [];
  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getPhrases().subscribe({
      next: (data) => { this.phrases = data; },
      error: (err) => { console.error('Error loading phrases', err); }
    });
  }
}
