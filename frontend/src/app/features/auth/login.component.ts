import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { AuthState } from '../../core/state/auth.state';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="min-h-[80vh] flex items-center justify-center">
      <div class="card w-full max-w-md bg-base-200 shadow-xl border border-base-300">
        <div class="card-body gap-4">
          <div class="text-center mb-2">
            <h1 class="text-3xl font-bold text-primary">SwarmScope</h1>
            <p class="text-base-content/60 text-sm mt-1">Sign in to your account</p>
          </div>

          <fieldset class="fieldset">
            <label class="fieldset-label">Email</label>
            <input class="input input-bordered w-full"
              type="email" [(ngModel)]="email" name="email"
              placeholder="you@example.com" autocomplete="email" />
          </fieldset>

          <fieldset class="fieldset">
            <label class="fieldset-label">Password</label>
            <input class="input input-bordered w-full"
              type="password" [(ngModel)]="password" name="password"
              placeholder="••••••••" autocomplete="current-password" />
          </fieldset>

          @if (error()) {
            <div class="alert alert-error text-sm py-2">
              <span>{{ error() }}</span>
            </div>
          }

          <button class="btn btn-primary w-full mt-2"
            (click)="login()" [disabled]="!email || !password || loading()">
            @if (loading()) {
              <span class="loading loading-spinner loading-sm"></span>
            }
            {{ loading() ? 'Signing in\u2026' : 'Sign In' }}
          </button>

          <p class="text-center text-sm text-base-content/60">
            Don't have an account?
            <a routerLink="/auth/register" class="link link-primary ml-1">Register</a>
          </p>
        </div>
      </div>
    </div>
  `,
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
    this.api.post<{ access_token: string; refresh_token: string }>('/auth/token', {
      email: this.email,
      password: this.password,
    }).subscribe({
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
