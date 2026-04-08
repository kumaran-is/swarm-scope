import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="min-h-[80vh] flex items-center justify-center">
      <div class="card w-full max-w-md bg-base-200 shadow-xl border border-base-300">
        <div class="card-body gap-4">
          <div class="text-center mb-2">
            <h1 class="text-3xl font-bold text-primary">SwarmScope</h1>
            <p class="text-base-content/60 text-sm mt-1">Create an account</p>
          </div>

          <fieldset class="fieldset">
            <label class="fieldset-label">Email</label>
            <input class="input input-bordered w-full"
              type="email" [(ngModel)]="email" name="email"
              placeholder="you@example.com" autocomplete="email" />
          </fieldset>

          <fieldset class="fieldset">
            <label class="fieldset-label">Full Name</label>
            <input class="input input-bordered w-full"
              type="text" [(ngModel)]="fullName" name="fullName"
              placeholder="Jane Smith" autocomplete="name" />
          </fieldset>

          <fieldset class="fieldset">
            <label class="fieldset-label">Password</label>
            <input class="input input-bordered w-full"
              type="password" [(ngModel)]="password" name="password"
              placeholder="Min. 8 characters" autocomplete="new-password" />
          </fieldset>

          <fieldset class="fieldset">
            <label class="fieldset-label">Confirm Password</label>
            <input class="input input-bordered w-full"
              type="password" [(ngModel)]="confirmPassword" name="confirmPassword"
              placeholder="••••••••" autocomplete="new-password" />
          </fieldset>

          @if (error()) {
            <div class="alert alert-error text-sm py-2">
              <span>{{ error() }}</span>
            </div>
          }

          @if (success()) {
            <div class="alert alert-success text-sm py-2">
              <span>Account created! Redirecting to sign in&hellip;</span>
            </div>
          }

          <button class="btn btn-primary w-full mt-2"
            (click)="register()" [disabled]="loading() || success()">
            @if (loading()) {
              <span class="loading loading-spinner loading-sm"></span>
            }
            {{ loading() ? 'Creating account\u2026' : 'Create Account' }}
          </button>

          <p class="text-center text-sm text-base-content/60">
            Already have an account?
            <a routerLink="/auth/login" class="link link-primary ml-1">Sign in</a>
          </p>
        </div>
      </div>
    </div>
  `,
})
export class RegisterComponent {
  private api = inject(ApiService);
  private router = inject(Router);

  email = '';
  fullName = '';
  password = '';
  confirmPassword = '';
  loading = signal(false);
  error = signal('');
  success = signal(false);

  register(): void {
    this.error.set('');
    if (this.password !== this.confirmPassword) {
      this.error.set('Passwords do not match.');
      return;
    }
    if (this.password.length < 8) {
      this.error.set('Password must be at least 8 characters.');
      return;
    }

    this.loading.set(true);
    this.api.post<{ id: string }>('/auth/register', {
      email: this.email,
      full_name: this.fullName,
      password: this.password,
    }).subscribe({
      next: () => {
        this.loading.set(false);
        this.success.set(true);
        setTimeout(() => this.router.navigate(['/auth/login']), 2000);
      },
      error: (err: Error) => {
        this.loading.set(false);
        this.error.set(err.message || 'Registration failed.');
      },
    });
  }
}
