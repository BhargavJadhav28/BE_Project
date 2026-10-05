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

	let activeStage = $state<string | null>(null);

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
	<div class="pipeline-header">
		<div>
			<h2 class="pipeline-title">Execution pipeline audit</h2>
			<p class="pipeline-subtitle">Deterministic transformation from sensor history to dispatch schedule</p>
		</div>

		<div class="pipeline-meta font-mono">
			<span class="source-tag" class:live={isLiveBackend}>
				{isLiveBackend ? 'FastAPI :8000' : 'Simulation'}
			</span>
			<span class="latency-tag">{latencyMs.toFixed(1)} ms</span>
		</div>
	</div>

	<div class="stages-container">
		<!-- Stage 1 -->
		<div class="stage-cell">
			<div class="stage-header-row">
				<span class="stage-num font-mono">01</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Data sanitizer</h3>
					<span class="stage-sub">Lookback buffer healing</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('sanitizer')}>
					{activeStage === 'sanitizer' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body font-mono">
				<div class="stat-line">
					<span class="stat-label">Buffer size</span>
					<span class="stat-val">{historyCount}h</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Feed status</span>
					<span class="stat-badge" class:healed={hasGap}>
						{hasGap ? `${gapHours}h healed` : 'Continuous'}
					</span>
				</div>
			</div>

			{#if activeStage === 'sanitizer'}
				<div class="stage-drawer font-mono">
					<p><strong>Input:</strong> 48h rolling sensor logs [T-48h..T]</p>
					<p><strong>Logic:</strong> ≤3h gap interpolation + night zero fill</p>
					<p><strong>Output:</strong> 49-row contiguous telemetry matrix</p>
				</div>
			{/if}
		</div>

		<!-- Stage 2 -->
		<div class="stage-cell">
			<div class="stage-header-row">
				<span class="stage-num font-mono">02</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Conditioning</h3>
					<span class="stage-sub">Origin-anchored context</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('conditioning')}>
					{activeStage === 'conditioning' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body font-mono">
				<div class="stat-line">
					<span class="stat-label">Origin [T]</span>
					<span class="stat-val">{originTime}</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Leakage</span>
					<span class="stat-badge">Zero (frozen)</span>
				</div>
			</div>

			{#if activeStage === 'conditioning'}
				<div class="stage-drawer font-mono">
					<p><strong>Input:</strong> Telemetry frozen at T + 24h NWP weather</p>
					<p><strong>Logic:</strong> Cyclical time encodings + explicit horizon index</p>
					<p><strong>Output:</strong> 24 horizon-conditioned feature vectors</p>
				</div>
			{/if}
		</div>

		<!-- Stage 3 -->
		<div class="stage-cell">
			<div class="stage-header-row">
				<span class="stage-num font-mono">03</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Model inference</h3>
					<span class="stage-sub">Parallel GBDT regressors</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('inference')}>
					{activeStage === 'inference' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body font-mono">
				<div class="stat-line">
					<span class="stat-label">Latency</span>
					<span class="stat-val highlight">{latencyMs.toFixed(1)} ms</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Peaks</span>
					<span class="stat-val">{peakPvKw.toFixed(0)} kW / {peakLoadKw.toFixed(0)} kW</span>
				</div>
			</div>

			{#if activeStage === 'inference'}
				<div class="stage-drawer font-mono">
					<p><strong>Models:</strong> Dual LightGBM histogram regressors</p>
					<p><strong>Speed:</strong> Evaluates all 24 horizons in parallel</p>
					<p><strong>Output:</strong> Raw unconstrained day-ahead predictions</p>
				</div>
			{/if}
		</div>

		<!-- Stage 4 -->
		<div class="stage-cell">
			<div class="stage-header-row">
				<span class="stage-num font-mono">04</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Physical guard</h3>
					<span class="stage-sub">Hardware & night bounds</span>
				</div>
				<button class="stage-btn font-mono" onclick={() => toggleStage('guard')}>
					{activeStage === 'guard' ? 'Close' : 'Inspect'}
				</button>
			</div>

			<div class="stage-body font-mono">
				<div class="stat-line">
					<span class="stat-label">Night zeroing</span>
					<span class="stat-badge">0.0 kW (GHI ≤ 0)</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Inverter cap</span>
					<span class="stat-val">50.0 kW</span>
				</div>
			</div>

			{#if activeStage === 'guard'}
				<div class="stage-drawer font-mono">
					<p><strong>Input:</strong> Raw predictions and forecast irradiance</p>
					<p><strong>Logic:</strong> Strict zeroing when sun is down; inverter ceiling</p>
					<p><strong>Output:</strong> Physically compliant power envelope</p>
				</div>
			{/if}
		</div>

		<!-- Stage 5 -->
		<div class="stage-cell">
			<div class="stage-header-row">
				<span class="stage-num font-mono">05</span>
				<div class="stage-title-group">
					<h3 class="stage-title">Battery dispatch</h3>
					<span class="stage-sub">Economic arbitrage</span>
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

			<div class="stage-body font-mono">
				<div class="stat-line">
					<span class="stat-label">24h Net</span>
					<span class="stat-val" class:surplus={netBalanceKwh >= 0} class:deficit={netBalanceKwh < 0}>
						{netBalanceKwh >= 0 ? '+' : ''}{netBalanceKwh.toFixed(1)} kWh
					</span>
				</div>
				<div class="stat-line">
					<span class="stat-label">Action</span>
					<span class="stat-badge" class:surplus-badge={netBalanceKwh >= 0} class:deficit-badge={netBalanceKwh < 0}>
						{netBalanceKwh >= 0 ? 'Charge storage' : 'Discharge storage'}
					</span>
				</div>
			</div>

			{#if activeStage === 'dispatch'}
				<div class="stage-drawer font-mono">
					<p><strong>Solar:</strong> {totalPvKwh.toFixed(1)} kWh ({solarCoveragePct}% coverage)</p>
					<p><strong>Load:</strong> {totalLoadKwh.toFixed(1)} kWh demand</p>
					<p><strong>Target:</strong> Optimizes BESS charge/discharge schedule</p>
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
		padding: 1.75rem 2rem 1.5rem;
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
	}

	.stage-cell:last-child {
		border-right: none;
	}

	/* Number + title on row one, inspect pill beneath the title */
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
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			transform 0.5s var(--ease);
	}

	.stage-btn:hover {
		background: var(--surface-sunken);
		color: var(--text-primary);
	}

	.stage-btn:active {
		transform: scale(0.97);
	}

	.stage-body {
		display: flex;
		flex-direction: column;
		font-family: var(--font-sans);
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
		font-family: var(--font-mono);
		color: var(--text-primary);
		font-weight: 500;
		font-size: 0.74rem;
		text-align: right;
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

	.stage-drawer {
		background: var(--surface-soft);
		box-shadow: inset 0 0 0 1px var(--hairline);
		border-radius: var(--radius-inner);
		padding: 0.8rem 0.9rem;
		font-family: var(--font-sans);
		font-size: 0.74rem;
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		color: var(--text-secondary);
	}

	.stage-drawer p {
		margin: 0;
		line-height: 1.5;
	}

	.stage-drawer strong {
		color: var(--text-primary);
		font-weight: 600;
	}

	@media (max-width: 760px) {
		.pipeline-header {
			padding-inline: 1.25rem;
		}

		.pipeline-title {
			font-size: 1.55rem;
		}
	}
</style>
