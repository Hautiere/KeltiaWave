import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { RecordAppComponent } from './record-app.component';

bootstrapApplication(RecordAppComponent, { providers: [provideHttpClient()] }).catch(console.error);
