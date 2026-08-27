import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { TranscribeAppComponent } from './transcribe-app.component';

bootstrapApplication(TranscribeAppComponent, { providers: [provideHttpClient()] })
  .catch(error => console.error(error));
