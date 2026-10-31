import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { LiveAppComponent } from './live-app.component';

bootstrapApplication(LiveAppComponent, { providers: [provideHttpClient()] }).catch(console.error);
