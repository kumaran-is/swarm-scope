import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { AuthState } from '../../core/state/auth.state';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="auth-container">
      <div class="auth-card">
        <h1>SwarmScope</h1>
        <p class="subtitle">Sign in to your account</p>

        <form (ngSubmit)="login()">
          <label>Email
            <input type="email" [(ngModel)]="email" name="email" required autocomplete="email" />
          </label>
          <label>Password
            <input type="password" [(ngModel)]="password" name="password" required autocomplete="current-password" />
          </label>
          @if (error()) {
            <p class="error">{{ error() }}</p>
          }
          <button type="submit" [disabled]="loading()">
            {{ loading() ? 'Signing in…' : 'Sign In' }}
          </button>
        </form>

        <p class="link">Don't have an account? <a routerLink="/auth/register">Register</a></p>
      </div>
    </div>
  `,
  styles: [`
    .auth-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #0a0a14; }
    .auth-card { background: #1e1e2e; border-radius: 12px; padding: 2.5rem; width: 100%; max-width: 400px; }
    h1 { text-align: center; margin-bottom: 0.25rem; }
    .subtitle { text-align: center; color: #888; margin-bottom: 2rem; font-size: 0.9rem; }
    form { display: flex; flex-direction: column; gap: 1rem; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.9rem; color: #ccc; }
    input { background: #0a0a14; border: 1px solid #444; border-radius: 6px; padding: 0.6rem 0.75rem; color: #fff; font-size: 1rem; }
    input:focus { outline: none; border-color: #7c3aed; }
    button[type="submit"] { background: #7c3aed; color: #fff; border: none; border-radius: 6px; padding: 0.75rem; cursor: pointer; font-size: 1rem; margin-top: 0.5rem; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .error { color: #f44336; font-size: 0.85rem; }
    .link { text-align: center; margin-top: 1.5rem; font-size: 0.9rem; color: #888; }
    a { color: #7c3aed; text-decoration: none; }
  `],
})
export class LoginComponent {
  private api = inject(ApiService);
  private router = inject(Router);
  private authState = inject(AuthState);

  email = '';
  password = '';
  loading = signal(false);
  error = signal('');

  login(): void {
    if (!this.email || !this.password) return;
    this.loading.set(true);
    this.error.set('');

    const formData = new FormData();
    formData.append('username', this.email);
    formData.append('password', this.password);

    this.api.postForm<{ access_token: string; refresh_token: string }>('/auth/token', formData).subscribe({
      next: (res) => {
        this.authState.setTokens(res.access_token, res.refresh_token);
        this.loading.set(false);
        this.router.navigate(['/scenarios']);
      },
      error: (err: Error) => {
        this.loading.set(false);
        this.error.set(err.message || 'Login failed. Check your credentials.');
      },
    });
  }
}
