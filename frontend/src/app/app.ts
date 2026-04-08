import { Component, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { ToastComponent } from './shared/components/toast/toast.component';
import { AuthState } from './core/state/auth.state';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ToastComponent],
  template: `
    <div class="min-h-screen bg-base-100">
      <nav class="navbar bg-base-200 border-b border-base-300 px-4 sticky top-0 z-50">
        <div class="navbar-start">
          <a routerLink="/" class="btn btn-ghost text-xl font-bold text-primary">
            SwarmScope
          </a>
        </div>
        <div class="navbar-center hidden lg:flex">
          <ul class="menu menu-horizontal px-1 gap-1">
            <li>
              <a routerLink="/scenarios" routerLinkActive="active"
                class="btn btn-ghost btn-sm">Scenarios</a>
            </li>
          </ul>
        </div>
        <div class="navbar-end gap-2">
          @if (auth.isAuthenticated()) {
            <button (click)="signOut()" class="btn btn-ghost btn-sm">Sign out</button>
          } @else {
            <a routerLink="/auth/login" class="btn btn-outline btn-sm btn-primary">Sign in</a>
          }
        </div>
      </nav>
      <main class="container mx-auto px-4 py-8 max-w-6xl">
        <router-outlet />
      </main>
      <app-toast />
    </div>
  `,
})
export class App {
  auth = inject(AuthState);
  private router = inject(Router);

  signOut(): void {
    this.auth.clearTokens();
    this.router.navigate(['/auth/login']);
  }
}
