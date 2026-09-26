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
		background: #09090C;
		border: 1px solid #1C1C24;
		border-radius: 8px;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	.pipeline-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid #1C1C24;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.pipeline-title {
		margin: 0;
		font-size: 1.05rem;
		font-weight: 600;
		color: #FFFFFF;
		letter-spacing: -0.01em;
	}

	.pipeline-subtitle {
		margin: 0.2rem 0 0;
		font-size: 0.8rem;
		color: #71717A;
	}

	.pipeline-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.75rem;
	}

	.source-tag {
		padding: 0.25rem 0.65rem;
		border-radius: 4px;
		background: #141418;
		border: 1px solid #27272A;
		color: #A1A1AA;
	}

	.source-tag.live {
		color: #FFFFFF;
		border-color: #3F3F46;
		background: #181820;
	}

	.latency-tag {
		color: #71717A;
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
			border-bottom: 1px solid #1C1C24;
		}
	}

	.stage-cell {
		padding: 1.25rem;
		border-right: 1px solid #1C1C24;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
		min-width: 0;
		background: #09090C;
	}

	.stage-cell:last-child {
		border-right: none;
	}

	.stage-header-row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 0.5rem;
	}

	.stage-num {
		font-size: 0.75rem;
		font-weight: 700;
		color: #52525B;
	}

	.stage-title-group {
		flex: 1;
		min-width: 0;
	}

	.stage-title {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #FFFFFF;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.stage-sub {
		display: block;
		font-size: 0.7rem;
		color: #71717A;
		margin-top: 0.15rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.stage-btn {
		background: #141418;
		border: 1px solid #27272A;
		color: #A1A1AA;
		border-radius: 4px;
		padding: 0.2rem 0.5rem;
		font-size: 0.68rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.stage-btn:hover {
		background: #27272A;
		color: #FFFFFF;
	}

	.stage-body {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		font-size: 0.725rem;
	}

	.stat-line {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.2rem 0;
	}

	.stat-label {
		color: #71717A;
	}

	.stat-val {
		color: #D4D4D8;
		font-weight: 500;
	}

	.stat-val.highlight {
		color: #FFFFFF;
	}

	.stat-val.surplus {
		color: #10B981;
	}

	.stat-val.deficit {
		color: #F43F5E;
	}

	.stat-badge {
		font-size: 0.68rem;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		background: #141418;
		color: #A1A1AA;
		border: 1px solid #27272A;
	}

	.stat-badge.healed {
		color: #E4E4E7;
		background: #27272A;
	}

	.stat-badge.surplus-badge {
		color: #10B981;
		background: rgba(16, 185, 129, 0.14);
		border-color: rgba(16, 185, 129, 0.28);
	}

	.stat-badge.deficit-badge {
		color: #F43F5E;
		background: rgba(244, 63, 94, 0.14);
		border-color: rgba(244, 63, 94, 0.28);
	}

	.energy-track {
		height: 3px;
		width: 100%;
		border-radius: 2px;
		overflow: hidden;
		display: flex;
		background: #181820;
	}

	.energy-fill {
		height: 100%;
	}

	.pv-fill {
		background: #F59E0B;
	}

	.load-fill {
		background: #38BDF8;
	}

	.stage-drawer {
		background: #050507;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		padding: 0.65rem 0.75rem;
		font-size: 0.68rem;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		color: #A1A1AA;
	}

	.stage-drawer p {
		margin: 0;
		line-height: 1.4;
	}

	.stage-drawer strong {
		color: #FFFFFF;
	}
</style>
