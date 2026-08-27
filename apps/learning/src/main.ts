import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { AppComponent } from './app/app';

bootstrapApplication(AppComponent, {
  providers: [provideHttpClient(withFetch())],
}).catch((error: unknown) => console.error(error));
