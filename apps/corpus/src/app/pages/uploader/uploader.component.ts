import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Component } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../core/api.service';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  selector: 'app-uploader',
  templateUrl: './uploader.component.html',
  styleUrls: ['./uploader.component.scss']
})
export class UploaderComponent {
  customText = '';
  customFile?: File;
  customPreviewUrl: string | null = null;
  customError: string | null = null;
  submitting = false;

  constructor(private api: ApiService) {}

  onCustomFile(ev: Event) {
    const input = ev.target as HTMLInputElement;
    this.customFile = input.files?.[0] || undefined;
    this.customError = null;
    if (this.customPreviewUrl) {
      URL.revokeObjectURL(this.customPreviewUrl);
      this.customPreviewUrl = null;
    }
    if (this.customFile) {
      this.customPreviewUrl = URL.createObjectURL(this.customFile);
    }
  }

  reset() {
    this.customText = '';
    this.customFile = undefined;
    if (this.customPreviewUrl) {
      URL.revokeObjectURL(this.customPreviewUrl);
      this.customPreviewUrl = null;
    }
    this.customError = null;
  }

  async submit() {
    if (!this.customFile || !this.customText.trim()) {
      this.customError = 'Enter a sentence and choose an audio file.';
      return;
    }

    try {
      this.submitting = true;
      const phrase = await firstValueFrom(
        this.api.createPhrase({ texte: this.customText.trim() })
      );
      await firstValueFrom(
        this.api.uploadAudio(phrase.id, this.customFile, this.customFile.name)
      );

      this.reset();
      alert('File uploaded.');
    } catch (e) {
      console.error(e);
      this.customError = 'Upload failed.';
    } finally {
      this.submitting = false;
    }
  }
}
