import { Injectable, signal, computed } from '@angular/core';

const ACCESS_KEY = 'ss_access_token';
const REFRESH_KEY = 'ss_refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthState {
  private _accessToken = signal<string | null>(localStorage.getItem(ACCESS_KEY));
  private _refreshToken = signal<string | null>(localStorage.getItem(REFRESH_KEY));

  readonly accessToken = this._accessToken.asReadonly();
  readonly refreshToken = this._refreshToken.asReadonly();
  readonly isAuthenticated = computed(() => this._accessToken() !== null);

  setTokens(access: string, refresh: string): void {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
    this._accessToken.set(access);
    this._refreshToken.set(refresh);
  }

  clearTokens(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    this._accessToken.set(null);
    this._refreshToken.set(null);
  }
}
