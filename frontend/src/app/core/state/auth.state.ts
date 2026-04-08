import { Injectable, signal, computed } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthState {
  private _accessToken = signal<string | null>(null);
  private _refreshToken = signal<string | null>(null);

  readonly accessToken = this._accessToken.asReadonly();
  readonly refreshToken = this._refreshToken.asReadonly();
  readonly isAuthenticated = computed(() => this._accessToken() !== null);

  setTokens(access: string, refresh: string): void {
    this._accessToken.set(access);
    this._refreshToken.set(refresh);
  }

  clearTokens(): void {
    this._accessToken.set(null);
    this._refreshToken.set(null);
  }
}
