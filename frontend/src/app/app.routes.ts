import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/scenarios', pathMatch: 'full' },
  {
    path: 'scenarios',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/scenario-intake/scenario-intake.component').then(
        (m) => m.ScenarioIntakeComponent
      ),
  },
  {
    path: 'scenarios/:id/world',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/world-editor/world-editor.component').then(
        (m) => m.WorldEditorComponent
      ),
  },
  {
    path: 'simulations/:id/control',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/simulation-control/simulation-control.component').then(
        (m) => m.SimulationControlComponent
      ),
  },
  {
    path: 'simulations/:id/dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/live-dashboard/live-dashboard.component').then(
        (m) => m.LiveDashboardComponent
      ),
  },
  {
    path: 'simulations/:id/intervene',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/intervention-console/intervention-console.component').then(
        (m) => m.InterventionConsoleComponent
      ),
  },
  {
    path: 'simulations/:id/chat',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/agent-chat/agent-chat.component').then(
        (m) => m.AgentChatComponent
      ),
  },
  {
    path: 'simulations/:id/report',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/report-viewer/report-viewer.component').then(
        (m) => m.ReportViewerComponent
      ),
  },
  {
    path: 'ensembles/:id',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/ensemble-viewer/ensemble-viewer.component').then(
        (m) => m.EnsembleViewerComponent
      ),
  },
  {
    path: 'library',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/scenario-library/scenario-library.component').then(
        (m) => m.ScenarioLibraryComponent
      ),
  },
  {
    path: 'auth/login',
    loadComponent: () =>
      import('./features/auth/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'auth/register',
    loadComponent: () =>
      import('./features/auth/register.component').then((m) => m.RegisterComponent),
  },
];
