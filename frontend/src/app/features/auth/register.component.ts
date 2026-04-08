import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="auth-container">
      <div class="auth-card">
        <h1>SwarmScope</h1>
        <p class="subtitle">Create an account</p>

        <form (ngSubmit)="register()">
          <label>Email
            <input type="email" [(ngModel)]="email" name="email" required autocomplete="email" />
          </label>
          <label>Full Name
            <input type="text" [(ngModel)]="fullName" name="fullName" required autocomplete="name" />
          </label>
          <label>Password
            <input type="password" [(ngModel)]="password" name="password" required autocomplete="new-password" />
          </label>
          <label>Confirm Password
            <input type="password" [(ngModel)]="confirmPassword" name="confirmPassword" required autocomplete="new-password" />
          </label>
          @if (error()) {
            <p class="error">{{ error() }}</p>
          }
          @if (success()) {
            <p class="success">Account created! <a routerLink="/auth/login">Sign in</a></p>
          }
          <button type="submit" [disabled]="loading() || success()">
            {{ loading() ? 'Creating account…' : 'Create Account' }}
          </button>
        </form>

        <p class="link">Already have an account? <a routerLink="/auth/login">Sign in</a></p>
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
    .success { color: #4caf50; font-size: 0.85rem; }
    .success a { color: #7c3aed; }
    .link { text-align: center; margin-top: 1.5rem; font-size: 0.9rem; color: #888; }
    a { color: #7c3aed; text-decoration: none; }
  `],
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
