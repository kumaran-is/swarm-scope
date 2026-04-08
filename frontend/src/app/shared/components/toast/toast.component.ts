import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container">
      @for (toast of toastService.toasts(); track toast.id) {
        <div class="toast" [class]="toast.type" (click)="toastService.dismiss(toast.id)">
          <span class="toast-icon">
            {{ toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : toast.type === 'warning' ? '⚠' : 'ℹ' }}
          </span>
          <span class="toast-message">{{ toast.message }}</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container { position: fixed; bottom: 1.5rem; right: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; z-index: 9999; }
    .toast { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1.25rem; border-radius: 8px; cursor: pointer; min-width: 250px; max-width: 400px; font-size: 0.9rem; animation: slide-in 0.2s ease; }
    @keyframes slide-in { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    .toast.success { background: #2e7d32; color: #fff; }
    .toast.error { background: #c62828; color: #fff; }
    .toast.warning { background: #e65100; color: #fff; }
    .toast.info { background: #1565c0; color: #fff; }
    .toast-icon { font-weight: 700; }
  `],
})
export class ToastComponent {
  toastService = inject(ToastService);
}
