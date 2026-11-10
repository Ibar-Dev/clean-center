import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { TokenResponse, User } from '../models';

const TOKEN_KEY = 'clean_center_token';
const USER_KEY = 'clean_center_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly tokenState = signal<string | null>(this.readStorage(TOKEN_KEY));
  private readonly userState = signal<User | null>(this.readUser());

  readonly token = this.tokenState.asReadonly();
  readonly user = this.userState.asReadonly();
  readonly isAuthenticated = computed(() => Boolean(this.tokenState()));

  async login(username: string, password: string): Promise<User> {
    const response = await firstValueFrom(
      this.http.post<TokenResponse>('/api/auth/login', { username, password }),
    );
    this.tokenState.set(response.access_token);
    this.userState.set(response.user);
    this.writeStorage(TOKEN_KEY, response.access_token);
    this.writeStorage(USER_KEY, JSON.stringify(response.user));
    return response.user;
  }

  logout(): void {
    this.tokenState.set(null);
    this.userState.set(null);
    this.removeStorage(TOKEN_KEY);
    this.removeStorage(USER_KEY);
  }

  private readUser(): User | null {
    const raw = this.readStorage(USER_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  }

  private readStorage(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  private writeStorage(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      // La sesión sigue activa en memoria si el navegador bloquea localStorage.
    }
  }

  private removeStorage(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch {
      // Nada que limpiar.
    }
  }
}
