import { provideHttpClient } from '@angular/common/http';
import { bootstrapApplication } from '@angular/platform-browser';
import { SubtitlesAppComponent } from './subtitles-app.component';

bootstrapApplication(SubtitlesAppComponent, { providers: [provideHttpClient()] })
  .catch(error => console.error(error));
