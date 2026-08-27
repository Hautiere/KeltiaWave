import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Enregistrement } from './enregistrement';

describe('Enregistrement', () => {
  let component: Enregistrement;
  let fixture: ComponentFixture<Enregistrement>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Enregistrement]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Enregistrement);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
