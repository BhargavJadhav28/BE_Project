<script lang="ts">
	import {
		Database,
		CloudSun,
		Cpu,
		Lock,
		TrendingUp,
		ShieldCheck,
		BatteryCharging,
		ArrowRight,
		ArrowDown,
		SlidersHorizontal,
		Zap,
		CheckCircle2,
		AlertTriangle,
		Layers
	} from '@lucide/svelte';

	interface Props {
		origin: string;
		historyCount: number;
		hasGap: boolean;
		gapHours: number;
		latencyMs: number;
		pvForecast: number[];
		loadForecast: number[];
		isLiveBackend: boolean;
		source: string;
	}

	let {
		origin = '',
		historyCount = 49,
		hasGap = false,
		gapHours = 0,
		latencyMs = 0,
		pvForecast = [],
		loadForecast = [],
		isLiveBackend = false,
		source = ''
	}: Props = $props();

	type BlockId = 'inputs' | 'engine' | 'outputs' | 'dispatch';
	let selectedBlock = $state<BlockId>('inputs');
	let showTechSpecs = $state(false);

	let totalPvKwh = $derived(pvForecast.reduce((acc, val) => acc + val, 0));
	let totalLoadKwh = $derived(loadForecast.reduce((acc, val) => acc + val, 0));
	let netBalanceKwh = $derived(totalPvKwh - totalLoadKwh);
	let peakPvKw = $derived(pvForecast.length ? Math.max(...pvForecast) : 0);
	let peakLoadKw = $derived(loadForecast.length ? Math.max(...loadForecast) : 0);

	let originTime = $derived(
		origin
			? origin.includes('T')
				? origin.split('T')[1].slice(0, 5)
				: origin.includes(' ')
					? origin.split(' ')[1].slice(0, 5)
					: origin.slice(11, 16) || origin
			: '—'
	);
</script>

<div class="architecture-panel">
	<!-- Panel Header -->
	<div class="panel-header">
		<div>
			<div class="panel-badge-row font-mono">
				<span class="badge-accent">END-TO-END ARCHITECTURE</span>
				<span class="badge-status">{isLiveBackend ? 'FastAPI Backend Online' : 'Simulation Mode'}</span>
			</div>
			<h2 class="panel-title">What the model takes, does, and outputs</h2>
			<p class="panel-subtitle">
				Complete dataflow from historical sensor logs to battery storage dispatch.
			</p>
		</div>

		<div class="panel-actions font-mono">
			<button 
				class="mode-btn"
				class:active={showTechSpecs}
				onclick={() => (showTechSpecs = !showTechSpecs)}
				title="Toggle between simple ASD-STE100 rules and low-level code/math parameters"
			>
				{showTechSpecs ? 'Show simple rules' : 'Show code specs'}
			</button>
			<span class="speed-tag">{latencyMs.toFixed(1)} ms latency</span>
		</div>
	</div>

	<!-- Visual 4-Step Diagram: The Core Visual Representation -->
	<div class="diagram-flow">
		<!-- Step 1: Takes (Inputs) -->
		<button 
			class="diagram-card inputs-card" 
			class:active={selectedBlock === 'inputs'}
			onclick={() => (selectedBlock = 'inputs')}
		>
			<div class="card-step font-mono">01 • TAKES</div>
			<div class="card-title-row">
				<div class="card-icon-box input-icon">
					<Database size={16} />
				</div>
				<h3 class="card-title">Input Feeds</h3>
			</div>
			<p class="card-desc">
				48h sensor history + 24h weather forecast.
			</p>

			<div class="card-pill-list font-mono">
				<span class="pill">T-48h sensor logs</span>
				<span class="pill">24h NWP weather</span>
				<span class="pill" class:pill-heal={hasGap}>
					{hasGap ? `${gapHours}h gap auto-healed` : 'Gap-free stream'}
				</span>
			</div>
		</button>

		<div class="flow-connector" aria-hidden="true">
			<ArrowRight size={18} class="connector-arrow desktop-arrow" />
			<ArrowDown size={18} class="connector-arrow mobile-arrow" />
		</div>

		<!-- Step 2: Does (Engine) -->
		<button 
			class="diagram-card engine-card" 
			class:active={selectedBlock === 'engine'}
			onclick={() => (selectedBlock = 'engine')}
		>
			<div class="card-step font-mono">02 • DOES</div>
			<div class="card-title-row">
				<div class="card-icon-box engine-icon">
					<Cpu size={16} />
				</div>
				<h3 class="card-title">Dual LightGBM</h3>
			</div>
			<p class="card-desc">
				Freezes origin at hour T. Predicts 24 hours at once.
			</p>

			<div class="card-pill-list font-mono">
				<span class="pill">Origin lock at T ({originTime})</span>
				<span class="pill">Parallel solar & load models</span>
				<span class="pill highlight-pill">{latencyMs.toFixed(1)} ms speed</span>
			</div>
		</button>

		<div class="flow-connector" aria-hidden="true">
			<ArrowRight size={18} class="connector-arrow desktop-arrow" />
			<ArrowDown size={18} class="connector-arrow mobile-arrow" />
		</div>

		<!-- Step 3: Outputs (Raw Predictions) -->
		<button 
			class="diagram-card outputs-card" 
			class:active={selectedBlock === 'outputs'}
			onclick={() => (selectedBlock = 'outputs')}
		>
			<div class="card-step font-mono">03 • OUTPUTS</div>
			<div class="card-title-row">
				<div class="card-icon-box output-icon">
					<TrendingUp size={16} />
				</div>
				<h3 class="card-title">Power Forecast</h3>
			</div>
			<p class="card-desc">
				Raw 24h generation and building demand curves.
			</p>

			<div class="card-pill-list font-mono">
				<span class="pill pv-pill">Solar peak: {peakPvKw.toFixed(0)} kW</span>
				<span class="pill load-pill">Load peak: {peakLoadKw.toFixed(0)} kW</span>
				<span class="pill">24 discrete hours (kW)</span>
			</div>
		</button>

		<div class="flow-connector" aria-hidden="true">
			<ArrowRight size={18} class="connector-arrow desktop-arrow" />
			<ArrowDown size={18} class="connector-arrow mobile-arrow" />
		</div>

		<!-- Step 4: Protects & Acts (Dispatch) -->
		<button 
			class="diagram-card dispatch-card" 
			class:active={selectedBlock === 'dispatch'}
			onclick={() => (selectedBlock = 'dispatch')}
		>
			<div class="card-step font-mono">04 • ACTS</div>
			<div class="card-title-row">
				<div class="card-icon-box dispatch-icon">
					<BatteryCharging size={16} />
				</div>
				<h3 class="card-title">Guard & Battery</h3>
			</div>
			<p class="card-desc">
				Clips to hardware bounds. Schedules battery storage.
			</p>

			<div class="card-pill-list font-mono">
				<span class="pill">0 kW night / 50 kW cap</span>
				<span class="pill" class:surplus-pill={netBalanceKwh >= 0} class:deficit-pill={netBalanceKwh < 0}>
					{netBalanceKwh >= 0 ? 'Charge battery' : 'Discharge battery'}
				</span>
				<span class="pill">Net: {netBalanceKwh >= 0 ? '+' : ''}{netBalanceKwh.toFixed(1)} kWh</span>
			</div>
		</button>
	</div>

	<!-- Interactive Walkthrough Explainer: Spacious, Readable ASD-STE100 -->
	<section class="walkthrough-section">
		<div class="walkthrough-box">
			{#if selectedBlock === 'inputs'}
				<!-- 01: Inputs Detail -->
				<div class="walkthrough-header">
					<div class="header-tag-row font-mono">
						<span class="block-number">STEP 01</span>
						<span class="block-scope">WHAT THE SYSTEM TAKES (INPUTS)</span>
					</div>
					<h3 class="walkthrough-heading">
						Collect sensor history, heal data gaps, and add 24-hour weather predictions
					</h3>
				</div>

				<div class="walkthrough-grid">
					{#if !showTechSpecs}
						<div class="info-card">
							<span class="info-kicker font-mono">INPUT FEED 1</span>
							<h4>48 Hours of Sensor History</h4>
							<p>The system ingests past electrical power readings from the facility meters. It looks at the last 48 hours to establish normal energy use.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">INPUT FEED 2</span>
							<h4>Why Past Readings (Lags) Matter</h4>
							<p>Power consumption repeats daily. The reading from <strong>24 hours ago (T-24h)</strong> is the daily baseline. The reading from <strong>1 hour ago (T-1h)</strong> gives the current trend.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">AUTOMATED CLEANER</span>
							<h4>Self-Healing Data Gaps</h4>
							<p>If sensor signals drop for <strong>3 hours or less</strong>, the system fills missing values automatically. If gaps exceed 3 hours, the system stops and raises an alarm.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">FORWARD WEATHER</span>
							<h4>24-Hour Numerical Weather Forecast</h4>
							<p>Combines sensor history with upcoming predictions of <strong>solar irradiance (W/m²)</strong>, <strong>outdoor temperature (°C)</strong>, and <strong>cloud cover (%)</strong>.</p>
						</div>
					{:else}
						<div class="spec-card font-mono">
							<span class="spec-kicker">DATA LOADER & SANITIZER MODULE</span>
							<code>ml_service/data/loader.py :: BaseTelemetrySource</code>
							<code>ml_service/features/sanitizer.py :: TelemetrySanitizer</code>
							<p><strong>Frequency:</strong> Enforces contiguous hourly index <code>freq='h'</code>.</p>
							<p><strong>Heuristics:</strong> Linear interpolation for gaps &le; 3h; Nocturnal zero-fill when GHI &le; 0; Structured <code>TelemetryGapError</code> on dropouts &gt; 3h.</p>
						</div>
					{/if}
				</div>

			{:else if selectedBlock === 'engine'}
				<!-- 02: Engine Detail -->
				<div class="walkthrough-header">
					<div class="header-tag-row font-mono">
						<span class="block-number">STEP 02</span>
						<span class="block-scope">WHAT THE MODEL DOES (PROCESSING)</span>
					</div>
					<h3 class="walkthrough-heading">
						Lock past data at hour T and predict all 24 hours at the same time
					</h3>
				</div>

				<div class="walkthrough-grid">
					{#if !showTechSpecs}
						<div class="info-card">
							<span class="info-kicker font-mono">CORE PRINCIPLE (ADR 0001)</span>
							<h4>Zero Data Leakage (Origin Lock)</h4>
							<p>All historical sensor data locks at hour T. The models cannot read future sensor data. This ensures honest evaluation and prevents artificial cheating.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">MODEL ARCHITECTURE</span>
							<h4>Dual Specialized LightGBM Regressors</h4>
							<p>Two separate gradient-boosted decision tree models run in parallel: one model learns solar panel behavior, and one model learns building load demand.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">HORIZON CONDITIONING</span>
							<h4>No Error Multiplication</h4>
							<p>The models calculate all 24 future hours at one time. They do not feed predicted numbers back into the model. This stops prediction errors from compounding.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">LATENCY BENCHMARK</span>
							<h4>Fast Laptop CPU Execution</h4>
							<p>Full 24-hour inference runs in <strong>under 25 milliseconds</strong> on standard CPUs. No heavy GPU hardware is required for operation.</p>
						</div>
					{:else}
						<div class="spec-card font-mono">
							<span class="spec-kicker">FEATURE PIPELINE & MODEL SPEC</span>
							<code>ml_service/features/pipeline.py :: FeaturePipeline</code>
							<code>ml_service/models/pv_model.py, load_model.py</code>
							<p><strong>Lag Features:</strong> <code>lag_0, lag_1, lag_23, lag_24, mean_6h, std_6h, mean_24h, std_24h</code></p>
							<p><strong>Hyperparameters:</strong> 150 estimators, max_depth=6, num_leaves=31, learning_rate=0.05</p>
							<p><strong>Conditioning:</strong> Conditioned on horizon index <code>h ∈ [1..24]</code> and cyclical trigonometric encodings.</p>
						</div>
					{/if}
				</div>

			{:else if selectedBlock === 'outputs'}
				<!-- 03: Outputs Detail -->
				<div class="walkthrough-header">
					<div class="header-tag-row font-mono">
						<span class="block-number">STEP 03</span>
						<span class="block-scope">WHAT THE MODEL PRODUCES (OUTPUTS)</span>
					</div>
					<h3 class="walkthrough-heading">
						Synchronous 24-hour forward power trajectories in kilowatts (kW)
					</h3>
				</div>

				<div class="walkthrough-grid">
					{#if !showTechSpecs}
						<div class="info-card">
							<span class="info-kicker font-mono">OUTPUT STREAM 1</span>
							<h4>Solar PV Generation (P̂_pv)</h4>
							<p>Predicted solar generation for each hour from T+1 to T+24. Reaches peak production around solar noon (up to 50 kW).</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">OUTPUT STREAM 2</span>
							<h4>Building Power Demand (P̂_load)</h4>
							<p>Predicted building electricity consumption. Tracks workday morning ramps, HVAC temperature cooling, and evening schedules.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">POWER VS ENERGY</span>
							<h4>Kilowatts (kW) to Kilowatt-Hours (kWh)</h4>
							<p>The models output instantaneous power rate in <strong>kW</strong> for each hour. Summing the 24 hours gives total daily energy in <strong>kWh</strong>.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">VERIFIED ACCURACY</span>
							<h4>Production Quality SLA</h4>
							<p>Tested across 4 full seasons: Solar PV error is <strong>0.26% nMAE</strong> (SLA &le; 5.0%). Building load error is <strong>2.99% nMAE</strong> (SLA &le; 6.0%).</p>
						</div>
					{:else}
						<div class="spec-card font-mono">
							<span class="spec-kicker">API RESPONSE SCHEMA</span>
							<code>POST /forecast/24h -> ForecastResponse</code>
							<p><strong>Response Keys:</strong> <code>timestamps: string[24], p_pv_forecast: float[24], p_load_forecast: float[24]</code></p>
							<p><strong>Metadata:</strong> Includes forecast origin, execution latency in milliseconds, and schema version.</p>
						</div>
					{/if}
				</div>

			{:else if selectedBlock === 'dispatch'}
				<!-- 04: Action & Dispatch Detail -->
				<div class="walkthrough-header">
					<div class="header-tag-row font-mono">
						<span class="block-number">STEP 04</span>
						<span class="block-scope">HOW THE SYSTEM PROTECTS & ACTS (DISPATCH)</span>
					</div>
					<h3 class="walkthrough-heading">
						Enforce physical inverter limits and schedule battery storage
					</h3>
				</div>

				<div class="walkthrough-grid">
					{#if !showTechSpecs}
						<div class="info-card">
							<span class="info-kicker font-mono">PHYSICAL LIMIT 1</span>
							<h4>Night Solar Zeroing</h4>
							<p>Solar panels cannot generate electricity in the dark. When solar irradiance is zero, solar generation is strictly set to <strong>0.0 kW</strong>.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">PHYSICAL LIMIT 2</span>
							<h4>Inverter Hardware Ceiling</h4>
							<p>Solar power cannot exceed the physical capacity of the inverter. Power is clipped at <strong>50.0 kW maximum</strong>.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">ENERGY ARBITRAGE</span>
							<h4>Solar Surplus: Charge Battery</h4>
							<p>When solar power exceeds building demand (Net &gt; 0), the extra energy charges the on-site battery storage system.</p>
						</div>

						<div class="info-card">
							<span class="info-kicker font-mono">ENERGY ARBITRAGE</span>
							<h4>Power Deficit: Discharge Battery</h4>
							<p>When building demand exceeds solar power (Net &lt; 0), the battery discharges energy to supply the building and avoid buying expensive grid electricity.</p>
						</div>
					{:else}
						<div class="spec-card font-mono">
							<span class="spec-kicker">POSTPROCESSING & BOUNDARY CODE</span>
							<code>ml_service/postprocessing/boundary_enforcer.py :: BoundaryEnforcer</code>
							<p><code>P̂_pv = clip(P̂_pv, 0.0, 50.0) · 1(GHI &gt; 0)</code></p>
							<p><code>P̂_load = clip(P̂_load, 10.0, 45.0 · 1.2)</code></p>
							<p><strong>Dispatch Metric:</strong> <code>P_net = P̂_pv - P̂_load</code> feeding downstream Linear/MILP battery state-of-charge schedule.</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</section>
</div>

<style>
	.architecture-panel {
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		padding: 1.75rem 2rem 1.4rem;
		border-bottom: 1px solid var(--hairline);
		flex-wrap: wrap;
		gap: 1rem 1.5rem;
	}

	.panel-badge-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		margin-bottom: 0.35rem;
	}

	.badge-accent {
		font-size: 0.65rem;
		font-weight: 700;
		color: var(--color-pv-ink);
		letter-spacing: 0.08em;
	}

	.badge-status {
		font-size: 0.64rem;
		color: var(--text-muted);
		background: var(--surface-sunken);
		padding: 0.15rem 0.55rem;
		border-radius: 999px;
	}

	.panel-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: 1.85rem;
		font-weight: 400;
		line-height: 1.1;
		letter-spacing: -0.015em;
		color: var(--text-primary);
	}

	.panel-subtitle {
		margin: 0.45rem 0 0;
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.panel-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.74rem;
	}

	.mode-btn {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		color: var(--text-secondary);
		padding: 0.35rem 0.8rem;
		border-radius: 999px;
		font-size: 0.72rem;
		cursor: pointer;
		transition: all 0.25s var(--ease);
	}

	.mode-btn:hover {
		color: var(--text-primary);
		background: var(--surface-soft);
	}

	.mode-btn.active {
		background: rgba(2, 132, 199, 0.15);
		color: var(--color-load-ink);
		border-color: rgba(2, 132, 199, 0.4);
	}

	.speed-tag {
		color: var(--text-muted);
	}

	/* Diagram Flow: 4 Horizontal Cards with Connectors */
	.diagram-flow {
		display: flex;
		align-items: stretch;
		padding: 1.5rem 2rem;
		background: rgba(18, 16, 14, 0.4);
		border-bottom: 1px solid var(--hairline);
		gap: 0.75rem;
		overflow-x: auto;
	}

	@media (max-width: 960px) {
		.diagram-flow {
			flex-direction: column;
		}

		:global(.desktop-arrow) {
			display: none !important;
		}

		:global(.mobile-arrow) {
			display: block !important;
		}

		.flow-connector {
			align-self: center;
			padding: 0.25rem 0;
		}
	}

	.diagram-card {
		flex: 1;
		min-width: 210px;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 1.25rem;
		text-align: left;
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		cursor: pointer;
		transition: all 0.3s var(--ease);
	}

	.diagram-card:hover {
		border-color: var(--hairline-strong);
		transform: translateY(-2px);
	}

	.diagram-card.active {
		background: var(--surface-soft);
		box-shadow: 0 4px 20px -6px rgba(0, 0, 0, 0.7);
	}

	.inputs-card.active { border-color: rgba(2, 132, 199, 0.5); }
	.engine-card.active { border-color: rgba(232, 137, 12, 0.5); }
	.outputs-card.active { border-color: rgba(99, 102, 241, 0.5); }
	.dispatch-card.active { border-color: rgba(18, 160, 113, 0.5); }

	.card-step {
		font-size: 0.62rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.08em;
	}

	.card-title-row {
		display: flex;
		align-items: center;
		gap: 0.55rem;
	}

	.card-icon-box {
		width: 28px;
		height: 28px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 8px;
		background: var(--surface);
		border: 1px solid var(--hairline);
	}

	.input-icon { color: var(--color-load-ink); }
	.engine-icon { color: var(--color-pv-ink); }
	.output-icon { color: #a5b4fc; }
	.dispatch-icon { color: var(--color-surplus-ink); }

	.card-title {
		margin: 0;
		font-size: 0.98rem;
		font-weight: 600;
		color: var(--text-primary);
		letter-spacing: -0.01em;
	}

	.card-desc {
		margin: 0;
		font-size: 0.76rem;
		color: var(--text-secondary);
		line-height: 1.4;
	}

	.card-pill-list {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		margin-top: auto;
		padding-top: 0.6rem;
		border-top: 1px solid var(--hairline);
		font-size: 0.68rem;
	}

	.pill {
		color: var(--text-muted);
		background: rgba(255, 255, 255, 0.025);
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.pill-heal {
		color: var(--color-pv-ink);
		background: var(--color-pv-muted);
	}

	.highlight-pill {
		color: var(--text-primary);
	}

	.pv-pill { color: var(--color-pv-ink); }
	.load-pill { color: var(--color-load-ink); }

	.surplus-pill {
		color: var(--color-surplus-ink);
		background: var(--color-surplus-muted);
	}

	.deficit-pill {
		color: var(--color-deficit-ink);
		background: var(--color-deficit-muted);
	}

	.flow-connector {
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--hairline-strong);
		user-select: none;
	}

	:global(.mobile-arrow) {
		display: none;
	}

	/* Walkthrough Section */
	.walkthrough-section {
		padding: 2rem;
		background: var(--surface-soft);
	}

	.walkthrough-box {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.walkthrough-header {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.header-tag-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
	}

	.block-number {
		font-size: 0.64rem;
		font-weight: 700;
		color: var(--color-pv-ink);
		background: rgba(232, 137, 12, 0.12);
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
	}

	.block-scope {
		font-size: 0.64rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.08em;
	}

	.walkthrough-heading {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--text-primary);
		letter-spacing: -0.01em;
	}

	.walkthrough-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1.25rem;
	}

	.info-card {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.info-kicker {
		font-size: 0.62rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		color: var(--text-muted);
	}

	.info-card h4 {
		margin: 0;
		font-size: 0.92rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.info-card p {
		margin: 0;
		font-size: 0.78rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.spec-card {
		grid-column: 1 / -1;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		font-size: 0.78rem;
	}

	.spec-kicker {
		font-size: 0.66rem;
		font-weight: 700;
		color: var(--color-pv-ink);
		letter-spacing: 0.08em;
	}

	.spec-card code {
		background: rgba(255, 255, 255, 0.04);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		color: var(--text-primary);
		display: inline-block;
	}

	.spec-card p {
		margin: 0;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	@media (max-width: 760px) {
		.panel-header,
		.walkthrough-section {
			padding-inline: 1.25rem;
		}

		.panel-title {
			font-size: 1.55rem;
		}
	}
</style>
