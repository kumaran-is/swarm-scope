import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgentService, Agent, ChatMessage } from '../../core/services/agent.service';

@Component({
  selector: 'app-agent-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="chat-layout">
      <!-- Sidebar -->
      <aside class="agent-sidebar">
        <div class="px-3 pt-3 pb-2">
          <div class="breadcrumbs text-xs mb-3">
            <ul>
              <li><a [routerLink]="['/scenarios']" style="color: var(--ss-text-muted);">Scenarios</a></li>
              <li><a [routerLink]="['/simulations', simId, 'dashboard']" style="color: var(--ss-text-muted);">Dashboard</a></li>
              <li style="color: var(--ss-text-secondary);">Chat</li>
            </ul>
          </div>
          <p class="text-xs font-semibold uppercase tracking-widest mb-3" style="color: var(--ss-text-muted);">Agents</p>
        </div>

        <div class="agent-list-scroll">
          @for (agent of agents(); track agent.id) {
            <button class="agent-card-btn" [class.agent-card-active]="selectedAgent()?.id === agent.id"
              (click)="selectAgent(agent)">
              <!-- Avatar circle -->
              <div class="agent-avatar">{{ agent.name.charAt(0).toUpperCase() }}</div>
              <div class="agent-info">
                <span class="agent-name">{{ agent.name }}</span>
                <span class="agent-role">{{ agent.role }}</span>
                <!-- Activation bar -->
                <div class="activation-track">
                  <div class="activation-fill" [style.width.%]="agent.activation_score * 100"></div>
                </div>
              </div>
            </button>
          } @empty {
            <p class="px-4 py-3 text-xs" style="color: var(--ss-text-muted); font-style: italic;">
              No chat-enabled agents. Run a simulation first.
            </p>
          }
        </div>
      </aside>

      <!-- Chat Panel -->
      <section class="chat-panel">
        @if (selectedAgent(); as agent) {
          <header class="chat-header">
            <div class="agent-avatar-sm">{{ agent.name.charAt(0).toUpperCase() }}</div>
            <div>
              <div class="font-semibold text-sm" style="color: var(--ss-text-primary);">{{ agent.name }}</div>
              <div class="text-xs" style="color: var(--ss-text-muted);">{{ agent.faction ?? 'No faction' }}</div>
            </div>
          </header>

          <div class="messages-area">
            @for (msg of messages(); track $index) {
              <div class="message" [class]="'message-' + msg.role">
                @if (msg.role === 'assistant') {
                  <div class="msg-label">{{ agent.name }}</div>
                }
                <div class="bubble" [class]="'bubble-' + msg.role">{{ msg.content }}</div>
              </div>
            }
            @if (thinking()) {
              <div class="message message-assistant">
                <div class="msg-label">{{ agent.name }}</div>
                <div class="bubble bubble-assistant thinking-bubble">
                  <span class="typing-dot"></span>
                  <span class="typing-dot"></span>
                  <span class="typing-dot"></span>
                </div>
              </div>
            }
          </div>

          <div class="input-bar">
            <input class="chat-input" [(ngModel)]="userInput"
              placeholder="Ask {{ agent.name }} something…"
              (keyup.enter)="send()" />
            <button class="send-btn" (click)="send()" [disabled]="thinking() || !userInput.trim()">
              &#8594;
            </button>
          </div>
        } @else {
          <div class="no-agent-selected">
            <div class="w-12 h-12 rounded-full flex items-center justify-center text-2xl mb-3"
              style="background: var(--ss-cyan-dim); border: 1px solid rgba(6,182,212,0.2);">
              &#128172;
            </div>
            <p class="text-sm" style="color: var(--ss-text-muted);">Select an agent to start chatting.</p>
          </div>
        }
      </section>
    </div>
  `,
  styles: [`
    .chat-layout {
      display: flex;
      height: calc(100vh - 56px);
      background: var(--ss-bg-base);
    }
    .agent-sidebar {
      width: 240px;
      flex-shrink: 0;
      border-right: 1px solid var(--ss-border);
      display: flex;
      flex-direction: column;
      background: var(--ss-bg-card);
    }
    .agent-list-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 0.5rem;
    }
    .agent-card-btn {
      width: 100%;
      background: transparent;
      border: 1px solid transparent;
      text-align: left;
      padding: 0.625rem 0.75rem;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: flex-start;
      gap: 0.625rem;
      margin-bottom: 0.25rem;
      transition: background 0.15s ease, border-color 0.15s ease;
    }
    .agent-card-btn:hover { background: var(--ss-bg-base); }
    .agent-card-active {
      background: var(--ss-cyan-dim) !important;
      border-color: rgba(6,182,212,0.25) !important;
    }
    .agent-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue));
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.8rem;
      color: #fff;
      flex-shrink: 0;
    }
    .agent-avatar-sm {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue));
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.75rem;
      color: #fff;
      flex-shrink: 0;
    }
    .agent-info { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
    .agent-name { font-weight: 600; font-size: 0.85rem; color: var(--ss-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .agent-role { font-size: 0.7rem; color: var(--ss-text-muted); }
    .activation-track { height: 2px; background: var(--ss-border); border-radius: 1px; margin-top: 4px; }
    .activation-fill { height: 100%; background: linear-gradient(90deg, var(--ss-cyan), var(--ss-blue)); border-radius: 1px; transition: width 0.5s ease; }

    .chat-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
    .chat-header {
      padding: 0.875rem 1.25rem;
      border-bottom: 1px solid var(--ss-border);
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--ss-bg-card);
    }
    .messages-area {
      flex: 1;
      overflow-y: auto;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .message { display: flex; flex-direction: column; gap: 3px; }
    .message-user { align-items: flex-end; }
    .message-assistant { align-items: flex-start; }
    .msg-label { font-size: 0.7rem; color: var(--ss-text-muted); padding: 0 4px; }
    .bubble {
      max-width: 72%;
      padding: 0.625rem 0.875rem;
      border-radius: 12px;
      font-size: 0.875rem;
      line-height: 1.5;
    }
    .bubble-user {
      background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue));
      color: #fff;
      border-radius: 12px 12px 4px 12px;
    }
    .bubble-assistant {
      background: var(--ss-bg-card);
      border: 1px solid var(--ss-border);
      color: var(--ss-text-primary);
      border-radius: 12px 12px 12px 4px;
    }
    .thinking-bubble {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 0.625rem 1rem;
    }

    .input-bar {
      display: flex;
      gap: 0.5rem;
      padding: 0.875rem 1.25rem;
      border-top: 1px solid var(--ss-border);
      background: var(--ss-bg-card);
    }
    .chat-input {
      flex: 1;
      background: var(--ss-bg-base);
      border: 1px solid var(--ss-border);
      border-radius: 8px;
      padding: 0.625rem 0.875rem;
      font-size: 0.875rem;
      color: var(--ss-text-primary);
      outline: none;
      transition: border-color 0.15s ease;
    }
    .chat-input:focus { border-color: var(--ss-cyan); }
    .chat-input::placeholder { color: var(--ss-text-muted); }
    .send-btn {
      background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue));
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 0.625rem 1.125rem;
      font-size: 1rem;
      cursor: pointer;
      transition: opacity 0.15s ease, box-shadow 0.15s ease;
    }
    .send-btn:hover:not(:disabled) { box-shadow: var(--ss-glow-cyan); }
    .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

    .no-agent-selected {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
  `],
})
export class AgentChatComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private agentService = inject(AgentService);

  simId = '';
  agents = signal<Agent[]>([]);
  selectedAgent = signal<Agent | null>(null);
  messages = signal<ChatMessage[]>([]);
  thinking = signal(false);
  userInput = '';

  ngOnInit(): void {
    this.simId = this.route.snapshot.paramMap.get('id') ?? '';
    this.agentService.list(this.simId).subscribe({
      next: (agents) => this.agents.set(agents.filter(a => a.is_chat_enabled)),
      error: (err) => console.error('Failed to load agents', err),
    });
  }

  selectAgent(agent: Agent): void {
    this.selectedAgent.set(agent);
    this.messages.set([]);
  }

  send(): void {
    const input = this.userInput.trim();
    if (!input || !this.selectedAgent()) return;

    this.messages.update((msgs) => [...msgs, { role: 'user', content: input }]);
    this.userInput = '';
    this.thinking.set(true);

    const agent = this.selectedAgent()!;
    this.agentService.chat(this.simId, agent.id, input).subscribe({
      next: (res) => {
        this.thinking.set(false);
        this.messages.update((msgs) => [...msgs, { role: 'assistant', content: res.message }]);
      },
      error: (err: Error) => {
        this.thinking.set(false);
        this.messages.update((msgs) => [
          ...msgs,
          { role: 'assistant', content: `Error: ${err.message}` },
        ]);
      },
    });
  }
}
