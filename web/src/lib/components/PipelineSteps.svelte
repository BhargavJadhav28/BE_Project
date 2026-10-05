<script lang="ts">
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

	let activeStage = $state<string | null>('conditioning');
	let showTechSpecs = $state(false);

	function toggleStage(id: string) {
		activeStage = activeStage === id ? null : id;
	}

	let totalPvKwh = $derived(pvForecast.reduce((acc, val) => acc + val, 0));
	let totalLoadKwh = $derived(loadForecast.reduce((acc, val) => acc + val, 0));
	let netBalanceKwh = $derived(totalPvKwh - totalLoadKwh);
	let peakPvKw = $derived(pvForecast.length ? Math.max(...pvForecast) : 0);
	let peakLoadKw = $derived(loadForecast.length ? Math.max(...loadForecast) : 0);

	let solarCoveragePct = $derived(
		totalLoadKwh > 0 ? Math.min(100, Math.round((totalPvKwh / totalLoadKwh) * 100)) : 100
	);

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

<div class="pipeline-panel">
	<!-- Header -->
	<div class="pipeline-header">
		<div>
			<h2 class="pipeline-title">Execution pipeline & architecture audit</h2>
			<p class="pipeline-subtitle">
				Deterministic 5-stage transformation from raw sensor readings to battery dispatch
			</p>
		</div>

		<div class="pipeline-meta font-mono">
			<button 
				class="mode-toggle-btn"
				class:active={showTechSpecs}
				onclick={() => (showTechSpecs = !showTechSpecs)}
				title="Toggle between ASD-STE100 operational rules and low-level code/math specifications"
			>
				{showTechSpecs ? 'Show simple rules' : 'Show technical specs'}
			</button>
			<span class="source-tag" class:live={isLiveBackend}>
				{isLiveBackend ? 'FastAPI :8000' : 'Simulation'}
			</span>
			<span class="latency-tag">{latencyMs.toFixed(1)} ms</span>
		</div>
	</div>

	<!-- Visual Dataflow Connector Ribbon -->
	<div class="dataflow-ribbon font-mono">
		<button 
			class="flow-node" 
			class:active={activeStage === 'sanitizer'}
			onclick={() => toggleStage('sanitizer')}
		>
			<span class="node-dot"></span>
			<span class="node-text">01 Data Sanitizer</span>
		</button>
		<div class="flow-arrow" aria-hidden="true">→</div>
		
		<button 
			class="flow-node highlight-node" 
			class:active={activeStage === 'conditioning'}
			onclick={() => toggleStage('conditioning')}
		>
			<span class="node-dot"></span>
			<span class="node-text">02 Lags & Origin Lock</span>
		</button>
		<div class="flow-arrow" aria-hidden="true">→</div>

		<button 
			class="flow-node" 
			class:active={activeStage === 'inference'}
			onclick={() => toggleStage('inference')}
		>
			<span class="node-dot"></span>
			<span class="node-text">03 Dual LightGBM</span>
		</button>
		<div class="flow-arrow" aria-hidden="true">→</div>

		<button 
			class="flow-node" 
			class:active={activeStage === 'guard'}
			onclick={() => toggleStage('guard')}
		>
			<span class="node-dot"></span>
			<span class="node-text">04 Physical Limits</span>
		</button>
		<div class="flow-arrow" aria-hidden="true">→</div>

		<button 
			class="flow-node" 
			class:active={activeStage === 'dispatch'}
			onclick={() => toggleStage('dispatch')}
		>
			<span class="node-dot"></span>
			<span class="node-text">05 Battery Dispatch</span>
		</button>
	</div>

	<!-- Stage Grid -->
	<div class="stages-container">
		<!-- Stage 01: Sanitizer -->
		<div class="stage-cell" class:is-active={activeStage === 'sanitizer'}>
			<div class="stage-header-row">
				<span class="stage-num font-mono">01</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Clean sensor data</h3>
					<span class="stage-sub">Self-healing history buffer</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('sanitizer')}>
					{activeStage === 'sanitizer' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body">
				<div class="stat-line">
					<span class="stat-label">Buffer window</span>
					<span class="stat-val font-mono">{historyCount}h contiguous</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Signal status</span>
					<span class="stat-badge" class:healed={hasGap}>
						{hasGap ? `${gapHours}h filled (Healed)` : 'Continuous stream'}
					</span>
				</div>
			</div>

			{#if activeStage === 'sanitizer'}
				<div class="stage-drawer">
					{#if !showTechSpecs}
						<div class="ste-box">
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE</span>
								<p>Collect 48 hours of sensor history before origin time T.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE</span>
								<p>If data gaps are 3 hours or less, fill missing values automatically.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE</span>
								<p>If data gaps exceed 3 hours, stop the pipeline and trigger an alarm.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE</span>
								<p>If the sun is down (irradiance = 0), force missing solar values to 0.0 kW.</p>
							</div>
						</div>
					{:else}
						<div class="spec-box font-mono">
							<p><strong>Input:</strong> 48h rolling sensor DataFrame [T-48h..T]</p>
							<p><strong>Algorithm:</strong> Linear interpolation for gaps ≤ 3h</p>
							<p><strong>Guard:</strong> Raise <code>TelemetryGapError</code> on dropouts &gt; 3h</p>
							<p><strong>Output:</strong> Contiguous 49-row matrix with zero null values</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Stage 02: Feature Lags & Origin Lock (FOCAL POINT FOR LAGS) -->
		<div class="stage-cell stage-lags-cell" class:is-active={activeStage === 'conditioning'}>
			<div class="stage-header-row">
				<span class="stage-num font-mono">02</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Feature lags & origin lock</h3>
					<span class="stage-sub">Historical memory frozen at time T</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('conditioning')}>
					{activeStage === 'conditioning' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body">
				<div class="stat-line">
					<span class="stat-label">Origin lock [T]</span>
					<span class="stat-val font-mono">{originTime} (Locked)</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Daily lag [T-24h]</span>
					<span class="stat-badge lag-badge">Yesterday baseline</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Momentum [T-1h]</span>
					<span class="stat-badge lag-badge">Immediate trend</span>
				</div>
			</div>

			{#if activeStage === 'conditioning'}
				<div class="stage-drawer">
					<!-- Visual Lag Architecture Map -->
					<div class="lag-visual-map">
						<div class="lag-map-header font-mono">
							<span>HOW LAGS WORK (ADR 0001)</span>
						</div>

						<div class="lag-timeline-graphic">
							<!-- Past section -->
							<div class="timeline-block past-block">
								<span class="block-label font-mono">PAST SENSOR MEMORY (LOCKED AT T)</span>
								<div class="lag-chips font-mono">
									<div class="lag-chip" title="Reading from 24 hours ago (matches daily cycle)">
										<span class="chip-time">T-24h</span>
										<span class="chip-desc">Daily baseline</span>
									</div>
									<div class="lag-chip" title="Rolling 6-hour power mean (moving energy level)">
										<span class="chip-time">T-6h..T</span>
										<span class="chip-desc">Rolling mean</span>
									</div>
									<div class="lag-chip" title="Reading from 1 hour ago (immediate ramp)">
										<span class="chip-time">T-1h</span>
										<span class="chip-desc">Momentum</span>
									</div>
									<div class="lag-chip origin-chip" title="Current reading right at the forecast moment">
										<span class="chip-time">T</span>
										<span class="chip-desc">Anchor</span>
									</div>
								</div>
							</div>

							<!-- Lock Barrier -->
							<div class="timeline-divider" title="History freezes here. Model cannot read future sensor data.">
								<span class="lock-icon font-mono">🔒 LOCK</span>
								<span class="divider-line"></span>
							</div>

							<!-- Future section -->
							<div class="timeline-block future-block">
								<span class="block-label font-mono">24H FORWARD HORIZON</span>
								<div class="horizon-chips font-mono">
									<div class="horizon-chip">T+1h</div>
									<div class="horizon-chip">T+2h</div>
									<div class="horizon-chip">...</div>
									<div class="horizon-chip">T+24h</div>
								</div>
								<span class="future-note font-mono">+ 24h Numerical Weather Forecast</span>
							</div>
						</div>
					</div>

					{#if !showTechSpecs}
						<div class="ste-box">
							<div class="ste-rule">
								<span class="rule-tag font-mono">DEFINITION</span>
								<p><strong>What is a lag?</strong> A lag is a sensor measurement from the past.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE 1</span>
								<p>Use the power from 24 hours ago (T-24h) as the daily baseline. Facilities follow daily human schedules.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE 2</span>
								<p>Use the power from 1 hour ago (T-1h) to detect whether power is ramping up or down.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE 3</span>
								<p>Lock all lags at origin hour T. Do not use predicted numbers as lags. This stops error cascade.</p>
							</div>
						</div>
					{:else}
						<div class="spec-box font-mono">
							<p><strong>Lag Features:</strong> <code>lag_0, lag_1, lag_23, lag_24</code></p>
							<p><strong>Rolling Windows:</strong> <code>mean_6h, std_6h, mean_24h, std_24h</code></p>
							<p><strong>Horizon Index:</strong> Conditioned explicitly on integer <code>h ∈ [1..24]</code></p>
							<p><strong>Advantage:</strong> Eliminates autoregressive multi-step drift. No feedback error loop.</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Stage 03: Parallel LightGBM -->
		<div class="stage-cell" class:is-active={activeStage === 'inference'}>
			<div class="stage-header-row">
				<span class="stage-num font-mono">03</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Predict power</h3>
					<span class="stage-sub">Parallel LightGBM models</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('inference')}>
					{activeStage === 'inference' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body">
				<div class="stat-line">
					<span class="stat-label">Inference speed</span>
					<span class="stat-val highlight font-mono">{latencyMs.toFixed(1)} ms</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Raw peaks</span>
					<span class="stat-val font-mono">{peakPvKw.toFixed(0)} kW / {peakLoadKw.toFixed(0)} kW</span>
				</div>
			</div>

			{#if activeStage === 'inference'}
				<div class="stage-drawer">
					{#if !showTechSpecs}
						<div class="ste-box">
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE</span>
								<p>Run two specialized gradient-boosted models at the same time: one for Solar PV and one for Building Load.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">RULE</span>
								<p>Predict all 24 future hours in one calculation. Do not loop step-by-step.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">PERFORMANCE</span>
								<p>Inference executes in under 25 milliseconds on standard laptop CPUs.</p>
							</div>
						</div>
					{:else}
						<div class="spec-box font-mono">
							<p><strong>Models:</strong> Dual <code>lightgbm.LGBMRegressor</code> (pv_model, load_model)</p>
							<p><strong>Hyperparameters:</strong> 150 trees, max_depth=6, num_leaves=31, lr=0.05</p>
							<p><strong>Validation SLA:</strong> PV daylight nMAE &le; 0.26%, Load nMAE &le; 2.99%</p>
							<p><strong>Output:</strong> Unconstrained 24-step raw numerical predictions</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Stage 04: Physical Limits -->
		<div class="stage-cell" class:is-active={activeStage === 'guard'}>
			<div class="stage-header-row">
				<span class="stage-num font-mono">04</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Enforce physical limits</h3>
					<span class="stage-sub">Inverter ceiling & night bounds</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('guard')}>
					{activeStage === 'guard' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body">
				<div class="stat-line">
					<span class="stat-label">Night rule</span>
					<span class="stat-badge font-mono">0.0 kW (GHI ≤ 0)</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Inverter cap</span>
					<span class="stat-val font-mono">50.0 kW maximum</span>
				</div>
			</div>

			{#if activeStage === 'guard'}
				<div class="stage-drawer">
					{#if !showTechSpecs}
						<div class="ste-box">
							<div class="ste-rule">
								<span class="rule-tag font-mono">PHYSICS 1</span>
								<p>Set solar generation strictly to 0.0 kW when the sun is down (solar irradiance &le; 0).</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">PHYSICS 2</span>
								<p>Limit solar generation to 50.0 kW. Solar panels cannot produce more power than the inverter rating.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">PHYSICS 3</span>
								<p>Keep facility power demand between 10.0 kW (baseload) and 45.0 kW (peak).</p>
							</div>
						</div>
					{:else}
						<div class="spec-box font-mono">
							<p><strong>Boundary Code:</strong> <code>ml_service/postprocessing/boundary_enforcer.py</code></p>
							<p><strong>Solar Clipping:</strong> <code>clip(P̂_pv, 0.0, 50.0) · 1(GHI &gt; 0)</code></p>
							<p><strong>Load Clipping:</strong> <code>clip(P̂_load, 0.0, 1.2 · 45.0 kW)</code></p>
							<p><strong>Output:</strong> Safe, physically realizable dispatch boundary</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Stage 05: Battery Storage Dispatch -->
		<div class="stage-cell" class:is-active={activeStage === 'dispatch'}>
			<div class="stage-header-row">
				<span class="stage-num font-mono">05</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Schedule battery</h3>
					<span class="stage-sub">Solar storage & cost reduction</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('dispatch')}>
					{activeStage === 'dispatch' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<!-- Clean Energy Split Meter -->
			<div class="energy-track" title="{solarCoveragePct}% Solar coverage of building load">
				<div class="energy-fill pv-fill" style="width: {solarCoveragePct}%;"></div>
				<div class="energy-fill load-fill" style="width: {100 - solarCoveragePct}%;"></div>
			</div>

			<div class="stage-body">
				<div class="stat-line">
					<span class="stat-label">24h Net energy</span>
					<span class="stat-val font-mono" class:surplus={netBalanceKwh >= 0} class:deficit={netBalanceKwh < 0}>
						{netBalanceKwh >= 0 ? '+' : ''}{netBalanceKwh.toFixed(1)} kWh
					</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Battery action</span>
					<span class="stat-badge" class:surplus-badge={netBalanceKwh >= 0} class:deficit-badge={netBalanceKwh < 0}>
						{netBalanceKwh >= 0 ? 'Charge battery' : 'Discharge battery'}
					</span>
				</div>
			</div>

			{#if activeStage === 'dispatch'}
				<div class="stage-drawer">
					{#if !showTechSpecs}
						<div class="ste-box">
							<div class="ste-rule">
								<span class="rule-tag font-mono">FORMULA</span>
								<p><strong>Net Power</strong> = Solar Power minus Building Load.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">SURPLUS</span>
								<p>When solar power exceeds building load (Net &gt; 0), charge excess energy into the battery.</p>
							</div>
							<div class="ste-rule">
								<span class="rule-tag font-mono">DEFICIT</span>
								<p>When building load exceeds solar power (Net &lt; 0), discharge the battery to avoid buying expensive grid electricity.</p>
							</div>
						</div>
					{:else}
						<div class="spec-box font-mono">
							<p><strong>Total Solar:</strong> {totalPvKwh.toFixed(1)} kWh ({solarCoveragePct}% load coverage)</p>
							<p><strong>Total Demand:</strong> {totalLoadKwh.toFixed(1)} kWh facility consumption</p>
							<p><strong>Optimization Target:</strong> Mixed-Integer Linear Program (MILP) cost arbitrage</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.pipeline-panel {
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	.pipeline-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		padding: 1.75rem 2rem 1.4rem;
		border-bottom: 1px solid var(--hairline);
		flex-wrap: wrap;
		gap: 1rem 1.5rem;
	}

	.pipeline-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: 1.85rem;
		font-weight: 400;
		line-height: 1.1;
		letter-spacing: -0.015em;
		color: var(--text-primary);
	}

	.pipeline-subtitle {
		margin: 0.45rem 0 0;
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.pipeline-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.74rem;
	}

	.mode-toggle-btn {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		color: var(--text-secondary);
		padding: 0.35rem 0.75rem;
		border-radius: 999px;
		font-size: 0.72rem;
		cursor: pointer;
		transition: all 0.25s var(--ease);
	}

	.mode-toggle-btn:hover {
		color: var(--text-primary);
		background: var(--surface-soft);
	}

	.mode-toggle-btn.active {
		background: rgba(2, 132, 199, 0.15);
		color: var(--color-load-ink);
		border-color: rgba(2, 132, 199, 0.4);
	}

	.source-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.8rem;
		border-radius: 999px;
		background: var(--surface-sunken);
		color: var(--text-secondary);
	}

	.source-tag::before {
		content: '';
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-pv);
	}

	.source-tag.live::before {
		background: var(--color-surplus);
	}

	.latency-tag {
		color: var(--text-muted);
	}

	/* Dataflow ribbon connecting the 5 stages */
	.dataflow-ribbon {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.65rem 1.5rem;
		background: rgba(18, 16, 14, 0.5);
		border-bottom: 1px solid var(--hairline);
		overflow-x: auto;
		gap: 0.5rem;
	}

	.flow-node {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		background: transparent;
		border: none;
		color: var(--text-muted);
		font-size: 0.72rem;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		cursor: pointer;
		white-space: nowrap;
		transition: all 0.25s var(--ease);
	}

	.flow-node:hover {
		color: var(--text-primary);
	}

	.flow-node.active {
		color: var(--text-primary);
		background: var(--surface-sunken);
		font-weight: 500;
	}

	.node-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--text-muted);
		transition: background-color 0.25s ease;
	}

	.flow-node.active .node-dot {
		background: var(--color-pv);
		box-shadow: 0 0 8px var(--color-pv);
	}

	.flow-node.highlight-node .node-dot {
		background: var(--color-load);
	}

	.flow-arrow {
		color: var(--hairline-strong);
		font-size: 0.8rem;
		user-select: none;
	}

	.stages-container {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		width: 100%;
	}

	@media (max-width: 992px) {
		.stages-container {
			grid-template-columns: 1fr;
		}

		.stage-cell {
			border-right: none !important;
			border-bottom: 1px solid var(--hairline);
		}

		.stage-cell:last-child {
			border-bottom: none;
		}
	}

	.stage-cell {
		padding: 1.6rem 1.4rem 1.5rem;
		border-right: 1px solid var(--hairline);
		display: flex;
		flex-direction: column;
		gap: 1.1rem;
		min-width: 0;
		background: transparent;
		transition: background-color 0.3s ease;
	}

	.stage-cell.is-active {
		background: rgba(255, 255, 255, 0.015);
	}

	.stage-cell:last-child {
		border-right: none;
	}

	.stage-header-row {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: start;
		gap: 0.7rem 0.75rem;
	}

	.stage-num {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--surface-sunken);
		box-shadow: inset 0 0 0 1px var(--hairline-strong);
		font-size: 0.66rem;
		font-weight: 500;
		color: var(--text-secondary);
	}

	.stage-title-group {
		min-width: 0;
	}

	.stage-title {
		margin: 0;
		font-size: 0.92rem;
		font-weight: 600;
		letter-spacing: -0.01em;
		color: var(--text-primary);
		line-height: 1.3;
	}

	.stage-sub {
		display: block;
		font-size: 0.74rem;
		color: var(--text-muted);
		margin-top: 0.15rem;
		line-height: 1.35;
	}

	.stage-btn {
		grid-column: 2;
		justify-self: start;
		font-family: var(--font-sans);
		color: var(--text-secondary);
		border-radius: 999px;
		padding: 0.28rem 0.8rem;
		font-size: 0.72rem;
		font-weight: 500;
		box-shadow: inset 0 0 0 1px var(--hairline-strong);
		cursor: pointer;
		transition: all 0.3s var(--ease);
	}

	.stage-btn:hover {
		background: var(--surface-sunken);
		color: var(--text-primary);
	}

	.stage-body {
		display: flex;
		flex-direction: column;
		font-size: 0.76rem;
	}

	.stat-line {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		padding: 0.55rem 0;
		border-top: 1px solid var(--hairline);
	}

	.stat-label {
		color: var(--text-muted);
	}

	.stat-val {
		color: var(--text-primary);
		font-weight: 500;
		font-size: 0.74rem;
		text-align: right;
	}

	.stat-val.highlight {
		color: var(--color-pv-ink);
	}

	.stat-val.surplus {
		color: var(--color-surplus-ink);
	}

	.stat-val.deficit {
		color: var(--color-deficit-ink);
	}

	.stat-badge {
		font-size: 0.68rem;
		font-weight: 500;
		padding: 0.15rem 0.6rem;
		border-radius: 999px;
		background: var(--surface-sunken);
		color: var(--text-secondary);
		text-align: right;
	}

	.stat-badge.lag-badge {
		background: rgba(2, 132, 199, 0.12);
		color: var(--color-load-ink);
	}

	.stat-badge.healed {
		color: var(--color-pv-ink);
		background: var(--color-pv-muted);
	}

	.stat-badge.surplus-badge {
		color: var(--color-surplus-ink);
		background: var(--color-surplus-muted);
	}

	.stat-badge.deficit-badge {
		color: var(--color-deficit-ink);
		background: var(--color-deficit-muted);
	}

	.energy-track {
		height: 6px;
		width: 100%;
		border-radius: 999px;
		overflow: hidden;
		display: flex;
		background: var(--surface-sunken);
	}

	.energy-fill {
		height: 100%;
	}

	.pv-fill {
		background: var(--color-pv);
	}

	.load-fill {
		background: var(--color-load);
	}

	/* Drawers */
	.stage-drawer {
		background: var(--surface-soft);
		box-shadow: inset 0 0 0 1px var(--hairline);
		border-radius: var(--radius-inner);
		padding: 0.9rem;
		font-size: 0.74rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		color: var(--text-secondary);
	}

	/* STE-100 Rule Box */
	.ste-box {
		display: flex;
		flex-direction: column;
		gap: 0.55rem;
	}

	.ste-rule {
		display: flex;
		flex-direction: column;
		gap: 0.18rem;
	}

	.rule-tag {
		font-size: 0.62rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.ste-rule p {
		margin: 0;
		line-height: 1.45;
		color: var(--text-primary);
	}

	.spec-box {
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		font-size: 0.72rem;
	}

	.spec-box p {
		margin: 0;
		line-height: 1.45;
	}

	.spec-box code {
		color: var(--color-pv-ink);
		background: var(--surface-sunken);
		padding: 0.1rem 0.35rem;
		border-radius: 3px;
	}

	/* Lag Visual Map Graphic */
	.lag-visual-map {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline);
		border-radius: 6px;
		padding: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}

	.lag-map-header {
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--color-load-ink);
		letter-spacing: 0.06em;
	}

	.lag-timeline-graphic {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}

	.timeline-block {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.block-label {
		font-size: 0.6rem;
		color: var(--text-muted);
		letter-spacing: 0.04em;
	}

	.lag-chips {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.4rem;
	}

	.lag-chip {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--hairline-strong);
		border-radius: 4px;
		padding: 0.35rem 0.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.lag-chip.origin-chip {
		border-color: rgba(2, 132, 199, 0.4);
		background: rgba(2, 132, 199, 0.1);
	}

	.chip-time {
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.chip-desc {
		font-size: 0.62rem;
		color: var(--text-muted);
	}

	.timeline-divider {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.2rem 0;
	}

	.lock-icon {
		font-size: 0.65rem;
		font-weight: 600;
		color: #eab308;
		background: rgba(234, 179, 8, 0.1);
		border: 1px solid rgba(234, 179, 8, 0.3);
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		white-space: nowrap;
	}

	.divider-line {
		flex: 1;
		height: 1px;
		background: dashed 1px var(--hairline-strong);
	}

	.horizon-chips {
		display: flex;
		gap: 0.35rem;
		flex-wrap: wrap;
	}

	.horizon-chip {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--hairline);
		padding: 0.2rem 0.45rem;
		border-radius: 3px;
		font-size: 0.66rem;
		color: var(--text-secondary);
	}

	.future-note {
		font-size: 0.62rem;
		color: var(--text-muted);
		margin-top: 0.2rem;
	}

	@media (max-width: 760px) {
		.pipeline-header {
			padding-inline: 1.25rem;
		}

		.pipeline-title {
			font-size: 1.55rem;
		}

		.lag-chips {
			grid-template-columns: 1fr;
		}
	}
</style>
