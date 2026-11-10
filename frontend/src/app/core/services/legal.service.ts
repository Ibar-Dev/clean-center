import { Injectable, signal } from '@angular/core';

export type LegalDocument = 'terms' | 'privacy';

@Injectable({ providedIn: 'root' })
export class LegalService {
  readonly current = signal<LegalDocument | null>(null);

  open(document: LegalDocument): void {
    this.current.set(document);
  }

  close(): void {
    this.current.set(null);
  }
}
