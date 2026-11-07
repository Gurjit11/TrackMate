import re

with open("app/static/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add .shine-text animation to <style>
shine_css = """
    @keyframes shine {
      0% { background-position: -200% center; }
      100% { background-position: 200% center; }
    }
    .shine-text {
      background: linear-gradient(90deg, #a78bfa 0%, #818cf8 20%, #38bdf8 40%, #ffffff 60%, #818cf8 80%, #a78bfa 100%);
      background-size: 200% auto;
      color: transparent;
      -webkit-background-clip: text;
      background-clip: text;
      animation: shine 3.5s linear infinite;
      font-weight: 800;
      letter-spacing: 0.025em;
      filter: drop-shadow(0 0 12px rgba(167, 139, 250, 0.45));
    }
  </style>"""

content = content.replace("  </style>", shine_css, 1)

# 2. Header full width and clean nav toggling
old_header_block = """  <header class="sticky top-0 z-50 glass-panel border-b border-slate-800/80">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        
        <!-- Logo & Brand Badge -->
        <div class="flex items-center space-x-3 cursor-pointer" onclick="goToHome()">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class="text-xl font-extrabold tracking-tight text-white">TrackMate</span>
              <span id="nav-mode-badge" class="px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">Consumer Portal</span>
            </div>
            <p id="nav-subtitle" class="text-[10px] text-slate-400">Autonomous Delivery Intelligence Platform</p>
          </div>
        </div>

        <!-- USER MODE NAVIGATION LINKS (Visible in User Mode) -->
        <nav id="user-nav-links" class="hidden md:flex items-center space-x-6 text-xs font-semibold text-slate-300">
          <a href="#tracking-section" class="hover:text-indigo-400 transition-colors">Live Tracking</a>
          <a href="#how-it-works-section" class="hover:text-indigo-400 transition-colors">How It Works</a>
          <a href="#architecture-section" class="hover:text-indigo-400 transition-colors">Agent Flow</a>
          <a href="#features-section" class="hover:text-indigo-400 transition-colors">Guardrails & Safety</a>
        </nav>

        <!-- DEVELOPER MODE TABS (Visible only in Developer Mode) -->
        <nav id="dev-nav-tabs" class="hidden items-center space-x-1">"""

new_header_block = """  <header class="sticky top-0 z-50 glass-panel border-b border-slate-800/80 w-full">
    <div class="w-full px-4 sm:px-6 lg:px-10">
      <div class="flex items-center justify-between h-16">
        
        <!-- Logo & Brand Badge -->
        <div class="flex items-center space-x-3 cursor-pointer" onclick="goToHome()">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class="text-xl font-extrabold tracking-tight text-white">TrackMate</span>
              <span id="nav-mode-badge" class="px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">Consumer Portal</span>
            </div>
            <p id="nav-subtitle" class="text-[10px] text-slate-400">Autonomous Delivery Intelligence Platform</p>
          </div>
        </div>

        <!-- USER MODE NAVIGATION LINKS (Visible in User Mode only) -->
        <nav id="user-nav-links" style="display: flex;" class="items-center space-x-6 text-xs font-semibold text-slate-300">
          <a href="#tracking-section" class="hover:text-indigo-400 transition-colors">Live Tracking</a>
          <a href="#how-it-works-section" class="hover:text-indigo-400 transition-colors">How It Works</a>
          <a href="#architecture-section" class="hover:text-indigo-400 transition-colors">Agent Flow</a>
          <a href="#features-section" class="hover:text-indigo-400 transition-colors">Guardrails & Safety</a>
        </nav>

        <!-- DEVELOPER MODE TABS (Visible only in Developer Mode) -->
        <nav id="dev-nav-tabs" style="display: none;" class="items-center space-x-1">"""

assert old_header_block in content, "old_header_block not matched"
content = content.replace(old_header_block, new_header_block, 1)

# 3. Replace How TrackMate Works Section with Minimalist Designer Diagram & PM/Dev Balanced Steps
arch_regex = re.compile(
    r'<!-- ARCHITECTURE & AGENT FLOW DIAGRAM \(ANIMATED & INTERACTIVE\) -->.*?'
    r'<!-- KEY CAPABILITIES & FEATURES GRID -->',
    re.DOTALL
)

new_architecture_section = """<!-- ARCHITECTURE & AGENT FLOW DIAGRAM (ANIMATED & INTERACTIVE) -->
    <section id="architecture-section" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-24 space-y-8">
      
      <div class="text-center space-y-2.5 max-w-2xl mx-auto">
        <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          <span>Architecture &amp; Intelligence Pipeline</span>
        </div>
        <h2 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">How TrackMate Works</h2>
        <p class="text-slate-400 text-xs sm:text-sm leading-relaxed">
          Click any step to inspect how product business goals translate into deterministic engineering execution.
        </p>
      </div>

      <!-- MINIMALIST DESIGNER 2-COLUMN WORKFLOW -->
      <div class="glass-panel rounded-2xl p-5 sm:p-7 border border-slate-800 shadow-2xl relative overflow-hidden">
        
        <!-- Sleek Minimal Controls Bar -->
        <div class="flex flex-wrap items-center justify-between gap-3 pb-4 mb-5 border-b border-slate-800/80">
          <div class="flex items-center space-x-2.5">
            <button 
              id="diagram-play-btn" 
              onclick="toggleDiagramPlay()" 
              class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-all flex items-center space-x-1.5 shadow-sm cursor-pointer"
            >
              <span id="diagram-play-icon">⏸</span>
              <span id="diagram-play-text">Pause</span>
            </button>
            <div class="flex items-center space-x-1">
              <button onclick="prevDiagramStep()" class="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white text-xs border border-slate-800 cursor-pointer" title="Previous Step">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
              </button>
              <button onclick="nextDiagramStep()" class="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white text-xs border border-slate-800 cursor-pointer" title="Next Step">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
              </button>
            </div>
            <div class="h-4 w-px bg-slate-800 mx-1"></div>
            <span class="text-xs font-mono text-slate-400">Stage <span id="diagram-current-step-label" class="text-indigo-400 font-bold">1</span> of 6</span>
          </div>

          <div class="flex items-center space-x-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span id="diagram-play-status-pill" class="text-[11px] font-mono text-slate-400">Auto-Advancing (3.8s)</span>
            <div class="w-24 h-1 bg-slate-800 rounded-full overflow-hidden ml-2">
              <div id="diagram-step-progress" class="h-full bg-indigo-500 transition-all duration-300" style="width: 16.6%;"></div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          <!-- LEFT COLUMN: PM + DEV BALANCED STEPS ACCORDION (5 Cols) -->
          <div class="lg:col-span-5 space-y-2.5" id="steps-accordion-container">
            
            <!-- Step 1 -->
            <div id="acc-card-1" onclick="selectDiagramStep(1, true)" class="acc-step-card p-3.5 rounded-xl border border-indigo-500/50 bg-slate-900/90 transition-all cursor-pointer hover:border-indigo-500 group">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span id="acc-badge-1" class="w-6 h-6 rounded-md bg-indigo-600 text-white font-bold text-[11px] flex items-center justify-center font-mono">01</span>
                  <h4 class="text-xs font-bold text-white group-hover:text-indigo-300 transition-colors">Inquiry Ingestion &amp; Triage</h4>
                </div>
                <div class="flex items-center space-x-2">
                  <span class="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">Triage</span>
                  <svg id="acc-chevron-1" class="w-3.5 h-3.5 text-indigo-400 transform rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </div>
              </div>
              <div id="acc-content-1" class="acc-content mt-2.5 text-xs text-slate-400 space-y-2 border-t border-slate-800/80 pt-2.5">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-indigo-300 flex items-center space-x-1">
                    <span>📌 Business / PM Goal:</span>
                  </span>
                  <p class="text-[11px] text-slate-300 leading-relaxed">
                    Auto-triages customer inquiries, normalizes messy tracking numbers, and prevents wasted agent cycles on invalid IDs.
                  </p>
                </div>
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                    <span>⚙️ Technical Mechanics:</span>
                  </span>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    Strips noise &amp; whitespace, validates regex pattern <code class="font-mono text-indigo-300">TM\d{4}</code>, and prepares payload.
                  </p>
                </div>
              </div>
            </div>

            <!-- Step 2 -->
            <div id="acc-card-2" onclick="selectDiagramStep(2, true)" class="acc-step-card p-3.5 rounded-xl border border-slate-800/90 bg-slate-900/40 transition-all cursor-pointer hover:border-slate-700 group">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span id="acc-badge-2" class="w-6 h-6 rounded-md bg-slate-800 text-slate-400 font-bold text-[11px] flex items-center justify-center font-mono">02</span>
                  <h4 class="text-xs font-bold text-slate-300 group-hover:text-white transition-colors">Shipment State Inspection</h4>
                </div>
                <div class="flex items-center space-x-2">
                  <span class="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded">Core DB</span>
                  <svg id="acc-chevron-2" class="w-3.5 h-3.5 text-slate-500 transform transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </div>
              </div>
              <div id="acc-content-2" class="acc-content hidden mt-2.5 text-xs text-slate-400 space-y-2 border-t border-slate-800/80 pt-2.5">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-cyan-300 flex items-center space-x-1">
                    <span>📌 Business / PM Goal:</span>
                  </span>
                  <p class="text-[11px] text-slate-300 leading-relaxed">
                    Evaluates promised delivery SLA against actual hub transit scans to distinguish genuine carrier delays from premature queries.
                  </p>
                </div>
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                    <span>⚙️ Technical Mechanics:</span>
                  </span>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    Executes <code class="font-mono text-cyan-300">get_shipment()</code>; extracts events and computes <code class="font-mono text-cyan-300">days_past_estimate</code> &amp; <code class="font-mono text-cyan-300">days_since_last_scan</code>.
                  </p>
                </div>
              </div>
            </div>

            <!-- Step 3 -->
            <div id="acc-card-3" onclick="selectDiagramStep(3, true)" class="acc-step-card p-3.5 rounded-xl border border-slate-800/90 bg-slate-900/40 transition-all cursor-pointer hover:border-slate-700 group">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span id="acc-badge-3" class="w-6 h-6 rounded-md bg-slate-800 text-slate-400 font-bold text-[11px] flex items-center justify-center font-mono">03</span>
                  <h4 class="text-xs font-bold text-slate-300 group-hover:text-white transition-colors">Weather Verification (M5)</h4>
                </div>
                <div class="flex items-center space-x-2">
                  <span class="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">Context</span>
                  <svg id="acc-chevron-3" class="w-3.5 h-3.5 text-slate-500 transform transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </div>
              </div>
              <div id="acc-content-3" class="acc-content hidden mt-2.5 text-xs text-slate-400 space-y-2 border-t border-slate-800/80 pt-2.5">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-amber-300 flex items-center space-x-1">
                    <span>📌 Business / PM Goal:</span>
                  </span>
                  <p class="text-[11px] text-slate-300 leading-relaxed">
                    Gives customers honest, transparent weather disruption details (cyclones, floods) without letting carrier excuses compromise refund rights.
                  </p>
                </div>
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                    <span>⚙️ Technical Mechanics:</span>
                  </span>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    Queries Open-Meteo API for destination hub coordinates across transit dates. Context only: strictly isolated from escalation triggers.
                  </p>
                </div>
              </div>
            </div>

            <!-- Step 4 -->
            <div id="acc-card-4" onclick="selectDiagramStep(4, true)" class="acc-step-card p-3.5 rounded-xl border border-slate-800/90 bg-slate-900/40 transition-all cursor-pointer hover:border-slate-700 group">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span id="acc-badge-4" class="w-6 h-6 rounded-md bg-slate-800 text-slate-400 font-bold text-[11px] flex items-center justify-center font-mono">04</span>
                  <h4 class="text-xs font-bold text-slate-300 group-hover:text-white transition-colors">Semantic Policy RAG</h4>
                </div>
                <div class="flex items-center space-x-2">
                  <span class="text-[10px] font-mono text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded">RAG</span>
                  <svg id="acc-chevron-4" class="w-3.5 h-3.5 text-slate-500 transform transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </div>
              </div>
              <div id="acc-content-4" class="acc-content hidden mt-2.5 text-xs text-slate-400 space-y-2 border-t border-slate-800/80 pt-2.5">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-purple-300 flex items-center space-x-1">
                    <span>📌 Business / PM Goal:</span>
                  </span>
                  <p class="text-[11px] text-slate-300 leading-relaxed">
                    Protects company margins by ensuring customer communications strictly adhere to contractual SLA clauses, claims limits, and refund windows.
                  </p>
                </div>
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                    <span>⚙️ Technical Mechanics:</span>
                  </span>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    Vector cosine similarity search in ChromaDB across segmented policy Markdown chunks; returns grounded clause IDs (<code class="font-mono text-purple-300">CLAUSE_REFUND_01</code>).
                  </p>
                </div>
              </div>
            </div>

            <!-- Step 5 -->
            <div id="acc-card-5" onclick="selectDiagramStep(5, true)" class="acc-step-card p-3.5 rounded-xl border border-slate-800/90 bg-slate-900/40 transition-all cursor-pointer hover:border-slate-700 group">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span id="acc-badge-5" class="w-6 h-6 rounded-md bg-slate-800 text-slate-400 font-bold text-[11px] flex items-center justify-center font-mono">05</span>
                  <h4 class="text-xs font-bold text-slate-300 group-hover:text-white transition-colors">Guardrails Shield (G1–G5)</h4>
                </div>
                <div class="flex items-center space-x-2">
                  <span class="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">Safety</span>
                  <svg id="acc-chevron-5" class="w-3.5 h-3.5 text-slate-500 transform transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </div>
              </div>
              <div id="acc-content-5" class="acc-content hidden mt-2.5 text-xs text-slate-400 space-y-2 border-t border-slate-800/80 pt-2.5">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-amber-300 flex items-center space-x-1">
                    <span>📌 Business / PM Goal:</span>
                  </span>
                  <p class="text-[11px] text-slate-300 leading-relaxed">
                    Guarantees zero AI hallucination: mandates human escalation for packages late by &gt;3 days and prevents unauthorized payout promises.
                  </p>
                </div>
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                    <span>⚙️ Technical Mechanics:</span>
                  </span>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    Five deterministic Python rules (G1 to G5) enforce schema output, strip unretrieved citations, and enforce auto-escalation gates.
                  </p>
                </div>
              </div>
            </div>

            <!-- Step 6 -->
            <div id="acc-card-6" onclick="selectDiagramStep(6, true)" class="acc-step-card p-3.5 rounded-xl border border-slate-800/90 bg-slate-900/40 transition-all cursor-pointer hover:border-slate-700 group">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span id="acc-badge-6" class="w-6 h-6 rounded-md bg-slate-800 text-slate-400 font-bold text-[11px] flex items-center justify-center font-mono">06</span>
                  <h4 class="text-xs font-bold text-slate-300 group-hover:text-white transition-colors">Resolution &amp; Human Outbox</h4>
                </div>
                <div class="flex items-center space-x-2">
                  <span class="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">Action</span>
                  <svg id="acc-chevron-6" class="w-3.5 h-3.5 text-slate-500 transform transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </div>
              </div>
              <div id="acc-content-6" class="acc-content hidden mt-2.5 text-xs text-slate-400 space-y-2 border-t border-slate-800/80 pt-2.5">
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-emerald-300 flex items-center space-x-1">
                    <span>📌 Business / PM Goal:</span>
                  </span>
                  <p class="text-[11px] text-slate-300 leading-relaxed">
                    Delivers professional consumer messaging while queuing carrier dispute actions for a supervisor's one-click sign-off.
                  </p>
                </div>
                <div class="space-y-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
                    <span>⚙️ Technical Mechanics:</span>
                  </span>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    Saves draft to local storage; calling <code class="font-mono text-emerald-300">POST /approve/{draft_id}</code> writes approved message idempotently to <code class="font-mono text-slate-300">outbox.jsonl</code>.
                  </p>
                </div>
              </div>
            </div>

          </div>

          <!-- RIGHT COLUMN: MINIMALIST PROFESSIONAL DIAGRAM & HUD INSPECTOR (7 Cols) -->
          <div class="lg:col-span-7 flex flex-col justify-between space-y-4">
            
            <!-- Compact Diagram Flow Canvas -->
            <div class="rounded-xl bg-slate-950/90 border border-slate-800/90 p-5 relative overflow-hidden shadow-inner">
              <div class="absolute inset-0 bg-gradient-to-b from-indigo-950/10 via-transparent to-slate-950 pointer-events-none"></div>
              
              <div class="relative z-10 space-y-3">
                
                <!-- Tier 1: Input -->
                <div class="flex justify-center">
                  <div id="d-node-1" onclick="selectDiagramStep(1, true)" class="diagram-node px-4 py-2 rounded-xl bg-slate-900 border-2 border-indigo-500 shadow-md shadow-indigo-500/20 transition-all cursor-pointer flex items-center space-x-2.5 hover:border-indigo-400">
                    <span class="w-5 h-5 rounded-md bg-indigo-600/30 text-indigo-400 text-xs flex items-center justify-center font-bold">01</span>
                    <span class="text-xs font-semibold text-white">Customer Query &amp; ID</span>
                  </div>
                </div>

                <!-- Connector 1 -->
                <div class="flex justify-center -my-1">
                  <svg class="w-24 h-4 text-indigo-500/60" viewBox="0 0 96 16" fill="none">
                    <path d="M48 0 V16" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3" />
                  </svg>
                </div>

                <!-- Tier 2: Grounding Grid (DB, Weather, RAG) -->
                <div class="grid grid-cols-3 gap-2.5">
                  <div id="d-node-2" onclick="selectDiagramStep(2, true)" class="diagram-node p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 transition-all cursor-pointer text-center space-y-1 hover:border-cyan-500/60">
                    <span class="text-[9px] font-mono font-bold text-cyan-400 uppercase block">02 &bull; DB</span>
                    <span class="text-[11px] font-semibold text-slate-200 block truncate">Shipment State</span>
                    <span class="text-[9px] font-mono text-slate-500">get_shipment</span>
                  </div>
                  <div id="d-node-3" onclick="selectDiagramStep(3, true)" class="diagram-node p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 transition-all cursor-pointer text-center space-y-1 hover:border-amber-500/60">
                    <span class="text-[9px] font-mono font-bold text-amber-400 uppercase block">03 &bull; M5</span>
                    <span class="text-[11px] font-semibold text-slate-200 block truncate">Open-Meteo</span>
                    <span class="text-[9px] font-mono text-slate-500">get_weather</span>
                  </div>
                  <div id="d-node-4" onclick="selectDiagramStep(4, true)" class="diagram-node p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 transition-all cursor-pointer text-center space-y-1 hover:border-purple-500/60">
                    <span class="text-[9px] font-mono font-bold text-purple-400 uppercase block">04 &bull; RAG</span>
                    <span class="text-[11px] font-semibold text-slate-200 block truncate">Vector Policies</span>
                    <span class="text-[9px] font-mono text-slate-500">search_policies</span>
                  </div>
                </div>

                <!-- Connector 2 -->
                <div class="flex justify-center -my-1">
                  <svg class="w-24 h-4 text-amber-500/60" viewBox="0 0 96 16" fill="none">
                    <path d="M48 0 V16" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3" />
                  </svg>
                </div>

                <!-- Tier 3: Safety Guardrails -->
                <div class="flex justify-center">
                  <div id="d-node-5" onclick="selectDiagramStep(5, true)" class="diagram-node px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 transition-all cursor-pointer flex items-center space-x-2.5 hover:border-amber-500">
                    <span class="w-5 h-5 rounded-md bg-amber-500/20 text-amber-400 text-xs flex items-center justify-center font-bold">05</span>
                    <span class="text-xs font-semibold text-slate-300">Deterministic Safety Shield (G1–G5)</span>
                  </div>
                </div>

                <!-- Connector 3 -->
                <div class="flex justify-center -my-1">
                  <svg class="w-24 h-4 text-emerald-500/60" viewBox="0 0 96 16" fill="none">
                    <path d="M48 0 V16" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3" />
                  </svg>
                </div>

                <!-- Tier 4: Final Output -->
                <div class="flex justify-center">
                  <div id="d-node-6" onclick="selectDiagramStep(6, true)" class="diagram-node px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 transition-all cursor-pointer flex items-center space-x-2.5 hover:border-emerald-500">
                    <span class="w-5 h-5 rounded-md bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center font-bold">06</span>
                    <span class="text-xs font-semibold text-slate-300">Customer Communication &amp; Human Outbox</span>
                  </div>
                </div>

              </div>
            </div>

            <!-- Sleek Live Inspector HUD Card -->
            <div class="rounded-xl bg-slate-900/90 border border-slate-800 p-4 space-y-2.5">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                  <span class="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
                  <span id="hud-step-title" class="text-xs font-bold text-white font-mono">Stage 01: Inquiry Ingestion &amp; Triage</span>
                </div>
                <span id="hud-badge" class="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">Input Sanitized</span>
              </div>
              <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1.5 font-mono text-[11px]">
                <div class="flex items-start space-x-1.5 text-slate-300">
                  <span class="text-indigo-400 font-bold select-none">PM:</span>
                  <span id="hud-pm-text" class="text-slate-300 font-sans text-xs">Captures query, normalizes format, identifies dispute urgency.</span>
                </div>
                <div class="flex items-start space-x-1.5 text-slate-400">
                  <span class="text-slate-500 font-bold select-none">DEV:</span>
                  <span id="hud-dev-code" class="text-indigo-300 select-all">normalize_id("tm1018") &rarr; regex check TM\\d{4}</span>
                </div>
              </div>
            </div>

          </div>

        </div>

      </div>

    </section>

    <!-- KEY CAPABILITIES & FEATURES GRID -->"""

match = arch_regex.search(content)
assert match, "Architecture section regex match failed"
content = content[:match.start()] + new_architecture_section + content[match.end():]

# 4. Remove old footer from user-mode-container
old_user_footer = """    <footer class="border-t border-slate-800/80 pt-10 text-center text-xs text-slate-500 space-y-3">
      <div class="flex items-center justify-center space-x-4">
        <button onclick="setAppMode('dev')" class="text-indigo-400 hover:text-indigo-300 font-semibold">Switch to Developer Console &rarr;</button>
        <span>&bull;</span>
        <a href="#tracking-section" class="hover:text-slate-400">Back to Top</a>
      </div>
      <p>TrackMate &copy; 2026 &bull; Autonomous Delivery Investigation System &bull; Built with FastAPI, LangChain & Gemini</p>
    </footer>"""

assert old_user_footer in content, "old_user_footer not found"
content = content.replace(old_user_footer, "", 1)

# 5. Insert Global Footer right after </main> (end of dev-mode-container)
global_footer = """  <!-- ========================================================================= -->
  <!-- GLOBAL FOOTER (Rendered in both User Mode and Developer Mode) -->
  <!-- ========================================================================= -->
  <footer class="w-full border-t border-slate-800/80 py-8 px-4 sm:px-6 lg:px-8 mt-12 text-center text-xs text-slate-500 space-y-4">
    <div class="flex items-center justify-center space-x-4">
      <button onclick="goToHome()" class="text-slate-400 hover:text-white transition-colors cursor-pointer">Home Portal</button>
      <span>&bull;</span>
      <button onclick="setAppMode(currentAppMode === 'user' ? 'dev' : 'user')" class="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors cursor-pointer">
        <span id="footer-mode-toggle-text">Switch to Developer Console &rarr;</span>
      </button>
      <span>&bull;</span>
      <a href="#tracking-section" class="text-slate-400 hover:text-white transition-colors">Back to Top</a>
    </div>

    <div class="pt-1">
      <div class="inline-flex items-center space-x-2.5 px-5 py-2.5 rounded-full bg-slate-900/90 border border-slate-700/80 shadow-xl shadow-indigo-500/10">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
        <span class="text-xs text-slate-300 font-medium">Designed &amp; built by <span class="shine-text text-sm ml-1">Gurjit Singh</span></span>
      </div>
    </div>

    <p class="text-[11px] text-slate-500 font-normal">TrackMate &copy; 2026 &bull; Autonomous Delivery Investigation Platform &bull; Built with FastAPI, LangChain &amp; Google Gemini</p>
  </footer>
"""

content = content.replace("  </main>\n\n  <!-- MODAL: RAW TRACE JSON INSPECTOR -->", f"  </main>\n\n{global_footer}\n  <!-- MODAL: RAW TRACE JSON INSPECTOR -->", 1)

# 6. Update JavaScript: setAppMode and Diagram Controller
old_set_app_mode = """      if (mode === 'user') {
        userBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all bg-indigo-600 text-white shadow";
        devBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-400 hover:text-white";
        userNav.classList.remove('hidden');
        devNav.classList.add('hidden');
        devNav.classList.remove('flex');
        devContainer.classList.add('hidden');
        userContainer.classList.remove('hidden');
        badge.innerText = "Consumer Portal";
        badge.className = "px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20";
        subtitle.innerText = "Autonomous Delivery Intelligence Platform";
      } else {
        devBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all bg-indigo-600 text-white shadow";
        userBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-400 hover:text-white";
        userNav.classList.add('hidden');
        devNav.classList.remove('hidden');
        devNav.classList.add('flex');
        userContainer.classList.add('hidden');
        devContainer.classList.remove('hidden');
        badge.innerText = "Developer Console";
        badge.className = "px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-indigo-500/15 text-indigo-400 border border-indigo-500/20";
        subtitle.innerText = "Multi-Tool Agentic Engine & Deterministic Guardrails";
        switchDevTab('investigate');
      }"""

new_set_app_mode = """      if (mode === 'user') {
        userBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all bg-indigo-600 text-white shadow";
        devBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-400 hover:text-white";
        userNav.style.display = 'flex';
        devNav.style.display = 'none';
        devContainer.classList.add('hidden');
        userContainer.classList.remove('hidden');
        badge.innerText = "Consumer Portal";
        badge.className = "px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20";
        subtitle.innerText = "Autonomous Delivery Intelligence Platform";
        const footerToggle = document.getElementById('footer-mode-toggle-text');
        if (footerToggle) footerToggle.innerText = "Switch to Developer Console →";
      } else {
        devBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all bg-indigo-600 text-white shadow";
        userBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-400 hover:text-white";
        userNav.style.display = 'none';
        devNav.style.display = 'flex';
        userContainer.classList.add('hidden');
        devContainer.classList.remove('hidden');
        badge.innerText = "Developer Console";
        badge.className = "px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-indigo-500/15 text-indigo-400 border border-indigo-500/20";
        subtitle.innerText = "Multi-Tool Agentic Engine & Deterministic Guardrails";
        const footerToggle = document.getElementById('footer-mode-toggle-text');
        if (footerToggle) footerToggle.innerText = "Switch to Consumer Portal →";
        switchDevTab('investigate');
      }"""

assert old_set_app_mode in content, "old_set_app_mode not found"
content = content.replace(old_set_app_mode, new_set_app_mode, 1)

