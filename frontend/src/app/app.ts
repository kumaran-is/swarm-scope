import { Component, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { ToastComponent } from './shared/components/toast/toast.component';
import { AuthState } from './core/state/auth.state';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ToastComponent],
  template: `
    <div class="min-h-screen" style="background-color: var(--ss-bg-base);">
      <nav class="sticky top-0 z-50 px-4" style="background: rgba(10,15,30,0.85); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid var(--ss-border);">
        <div class="flex items-center justify-between h-14 max-w-6xl mx-auto">
          <!-- Logo -->
          <a routerLink="/" class="flex items-center gap-2 group no-underline" style="text-decoration: none;">
            <div class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold"
              style="background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue)); box-shadow: var(--ss-glow-cyan);">
              ⬡
            </div>
            <span class="text-lg font-bold tracking-tight"
              style="color: var(--ss-cyan); text-shadow: 0 0 20px rgba(6,182,212,0.5);">
              SwarmScope
            </span>
          </a>

          <!-- Nav links -->
          <ul class="hidden lg:flex items-center gap-1 list-none m-0 p-0">
            <li>
              <a routerLink="/scenarios" routerLinkActive="nav-active"
                class="nav-link px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 no-underline"
                style="color: var(--ss-text-secondary);">
                Scenarios
              </a>
            </li>
          </ul>

          <!-- Auth -->
          <div class="flex items-center gap-2">
            @if (auth.isAuthenticated()) {
              <button (click)="signOut()"
                class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer border-0"
                style="background: transparent; color: var(--ss-text-secondary);"
                onmouseover="this.style.color='var(--ss-text-primary)'"
                onmouseout="this.style.color='var(--ss-text-secondary)'">
                Sign out
              </button>
            } @else {
              <a routerLink="/auth/login"
                class="px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-200 no-underline"
                style="background: var(--ss-cyan-dim); color: var(--ss-cyan); border: 1px solid rgba(6,182,212,0.3);">
                Sign in
              </a>
            }
          </div>
        </div>
        <!-- Animated gradient bottom border -->
        <div style="height: 1px; background: linear-gradient(90deg, transparent, var(--ss-cyan), var(--ss-blue), transparent); opacity: 0.5; margin-top: -1px;"></div>
      </nav>

      <main class="container mx-auto px-4 py-8 max-w-6xl">
        <router-outlet />
      </main>
      <app-toast />
    </div>
  `,
  styles: [`
    .nav-link:hover {
      color: var(--ss-cyan) !important;
      background: var(--ss-cyan-dim);
    }
    .nav-active {
      color: var(--ss-cyan) !important;
      background: var(--ss-cyan-dim);
    }
  `],
})
export class App {
  auth = inject(AuthState);
  private router = inject(Router);

  signOut(): void {
    this.auth.clearTokens();
    this.router.navigate(['/auth/login']);
  }
}
