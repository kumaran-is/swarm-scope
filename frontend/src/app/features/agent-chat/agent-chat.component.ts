import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgentService, Agent, ChatMessage } from '../../core/services/agent.service';

@Component({
  selector: 'app-agent-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="chat-layout">
      <aside class="agent-list">
        <h2>Agents</h2>
        @for (agent of agents(); track agent.id) {
          <button
            class="agent-btn"
            [class.active]="selectedAgent()?.id === agent.id"
            (click)="selectAgent(agent)"
          >
            <span class="agent-name">{{ agent.name }}</span>
            <span class="agent-role">{{ agent.role }}</span>
            <span class="activation" [style.width.%]="agent.activation_score * 100"></span>
          </button>
        } @empty {
          <p class="empty-state">No agents loaded.</p>
        }
      </aside>

      <section class="chat-panel">
        @if (selectedAgent(); as agent) {
          <header class="chat-header">
            <strong>{{ agent.name }}</strong>
            <span class="faction">{{ agent.faction ?? 'No faction' }}</span>
          </header>
          <div class="messages">
            @for (msg of messages(); track $index) {
              <div class="message" [class]="msg.role">
                <span class="bubble">{{ msg.content }}</span>
              </div>
            }
            @if (thinking()) {
              <div class="message assistant">
                <span class="bubble thinking">Thinking…</span>
              </div>
            }
          </div>
          <div class="input-row">
            <input
              [(ngModel)]="userInput"
              placeholder="Ask {{ agent.name }} something…"
              (keyup.enter)="send()"
            />
            <button (click)="send()" [disabled]="thinking() || !userInput.trim()">Send</button>
          </div>
        } @else {
          <div class="no-agent">Select an agent to start chatting.</div>
        }
      </section>
    </div>
  `,
  styles: [`
    .chat-layout { display: flex; height: calc(100vh - 60px); }
    .agent-list { width: 240px; border-right: 1px solid #2a2a3e; overflow-y: auto; padding: 1rem; }
    .agent-list h2 { font-size: 0.9rem; color: #888; margin-bottom: 0.75rem; }
    .agent-btn { width: 100%; background: none; border: none; text-align: left; padding: 0.6rem 0.75rem; border-radius: 6px; cursor: pointer; display: flex; flex-direction: column; gap: 0.2rem; margin-bottom: 0.25rem; position: relative; overflow: hidden; }
    .agent-btn.active { background: #2a2a3e; }
    .agent-btn:hover { background: #1e1e2e; }
    .agent-name { font-weight: 600; font-size: 0.9rem; color: #fff; }
    .agent-role { font-size: 0.75rem; color: #888; }
    .activation { position: absolute; bottom: 0; left: 0; height: 2px; background: #7c3aed; }
    .chat-panel { flex: 1; display: flex; flex-direction: column; }
    .chat-header { padding: 1rem 1.5rem; border-bottom: 1px solid #2a2a3e; display: flex; gap: 1rem; align-items: baseline; }
    .faction { font-size: 0.8rem; color: #888; }
    .messages { flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem; }
    .message { display: flex; }
    .message.user { justify-content: flex-end; }
    .message.assistant { justify-content: flex-start; }
    .bubble { max-width: 70%; padding: 0.6rem 1rem; border-radius: 12px; font-size: 0.9rem; line-height: 1.4; }
    .message.user .bubble { background: #7c3aed; color: #fff; }
    .message.assistant .bubble { background: #1e1e2e; color: #ccc; }
    .thinking { opacity: 0.6; font-style: italic; }
    .input-row { display: flex; gap: 0.5rem; padding: 1rem 1.5rem; border-top: 1px solid #2a2a3e; }
    .input-row input { flex: 1; background: #1e1e2e; border: 1px solid #444; border-radius: 6px; padding: 0.6rem 1rem; color: inherit; }
    .input-row button { background: #7c3aed; color: #fff; border: none; border-radius: 6px; padding: 0.6rem 1.2rem; cursor: pointer; }
    .input-row button:disabled { opacity: 0.5; cursor: not-allowed; }
    .no-agent { flex: 1; display: flex; align-items: center; justify-content: center; color: #888; font-style: italic; }
    .empty-state { color: #888; font-style: italic; font-size: 0.85rem; }
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
      next: (agents) => this.agents.set(agents.slice(0, 10)),
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
        this.messages.update((msgs) => [...msgs, { role: 'assistant', content: res.response }]);
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
