<script lang="ts">
	import type { HistoricalReading, WeatherForecastStep } from '../types';

	interface Props {
		history: HistoricalReading[];
		weather: WeatherForecastStep[];
	}

	let { history = [], weather = [] }: Props = $props();

	type TabId = 'weather' | 'history' | 'specs' | 'parameters';
	let activeTab = $state<TabId>('history');
</script>

<div class="drawer-panel">
	<!-- Tab Bar -->
	<div class="drawer-tabs">
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'history'}
			onclick={() => (activeTab = 'history')}
		>Historical Sensor Lags ({history.length}h)</button>
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'weather'}
			onclick={() => (activeTab = 'weather')}
		>Forward Weather Forecast ({weather.length}h)</button>
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'specs'}
			onclick={() => (activeTab = 'specs')}
		>Asset Limits & Model Specs</button>
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'parameters'}
			onclick={() => (activeTab = 'parameters')}
		>Parameters & Units</button>
	</div>

	<!-- Content Body -->
	<div class="drawer-body">
		{#if activeTab === 'weather'}
			<div class="tab-explainer font-mono">
				<span class="explainer-tag">FORWARD WEATHER</span>
				<p>Numerical Weather Predictions (NWP) for the next 24 hours. The models use forecasted solar irradiance (GHI) and ambient temperature to predict upcoming generation and air-conditioning demand.</p>
			</div>

			<div class="table-container font-mono">
				<table class="data-table">
					<thead>
						<tr>
							<th>Horizon</th>
							<th>Target timestamp</th>
							<th>Irradiance (GHI)</th>
							<th>Temperature</th>
							<th>Cloud cover</th>
							<th>Solar state</th>
						</tr>
					</thead>
					<tbody>
						{#each weather as row, i}
							<tr>
								<td class="horizon-cell">T+{i + 1}</td>
								<td class="time-cell">{row.timestamp.replace('T', ' ')}</td>
								<td>
									<div class="cell-with-bar">
										<span class="pv-text">{row.ghi.toFixed(1)} W/m²</span>
										<div class="bar-track">
											<div class="bar-fill pv-fill" style="width: {Math.min(100, (row.ghi / 1000) * 100)}%;"></div>
										</div>
									</div>
								</td>
								<td>{row.temp_amb.toFixed(1)} °C</td>
								<td>
									<div class="cell-with-bar">
										<span>{row.cloud_cover.toFixed(0)}%</span>
										<div class="bar-track">
											<div class="bar-fill cloud-fill" style="width: {row.cloud_cover}%;"></div>
										</div>
									</div>
								</td>
								<td>
									{#if row.ghi > 0}
										<span class="status-tag daylight">Daylight</span>
									{:else}
										<span class="status-tag night">Night (0 kW)</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else if activeTab === 'history'}
			<!-- ASD-STE100 Lag Explainer -->
			<div class="tab-explainer lag-banner font-mono">
				<div class="explainer-header">
					<span class="explainer-tag highlight-tag">FEATURE LAGS IN THIS TABLE</span>
					<span class="explainer-note">Origin locked at T</span>
				</div>
				<p>
					<strong>What is a lag?</strong> A lag is a sensor measurement from the past.
					The models lock at row <strong>T (Origin)</strong>. They read <strong>T</strong> (current power), <strong>T-1h</strong> (momentum), and <strong>T-24h</strong> (yesterday's daily baseline).
					All historical readings stay frozen. The model never reads future data.
				</p>
			</div>

			<div class="table-container font-mono">
				<table class="data-table">
					<thead>
						<tr>
							<th>Lag anchor</th>
							<th>Timestamp</th>
							<th>Solar generation</th>
							<th>Facility load</th>
							<th>Irradiance (GHI)</th>
							<th>Temperature</th>
							<th>Model function</th>
						</tr>
					</thead>
					<tbody>
						{#each history.slice(-25) as row, i}
							{@const lagHours = 24 - i}
							{@const isOrigin = lagHours === 0}
							{@const isLag1 = lagHours === 1}
							{@const isLag23 = lagHours === 23}
							{@const isLag24 = lagHours === 24}
							<tr class:highlight-row={isOrigin || isLag1 || isLag24}>
								<td class="horizon-cell">
									{#if isOrigin}
										<span class="anchor-badge origin-badge">T (Origin)</span>
									{:else if isLag1}
										<span class="anchor-badge momentum-badge">T-1h</span>
									{:else if isLag24}
										<span class="anchor-badge baseline-badge">T-24h</span>
									{:else}
										T-{lagHours}h
									{/if}
								</td>
								<td class="time-cell">{row.timestamp.replace('T', ' ')}</td>
								<td class="pv-text font-bold">{row.p_pv.toFixed(2)} kW</td>
								<td class="load-text font-bold">{row.p_load.toFixed(2)} kW</td>
								<td>{row.ghi.toFixed(1)} W/m²</td>
								<td>{row.temp_amb.toFixed(1)} °C</td>
								<td>
									{#if isOrigin}
										<span class="func-pill origin-pill">🔒 Current level (Anchor)</span>
									{:else if isLag1}
										<span class="func-pill momentum-pill">📈 Immediate ramp</span>
									{:else if isLag24}
										<span class="func-pill baseline-pill">🔁 Daily baseline match</span>
									{:else if isLag23}
										<span class="func-pill">23h lead-in</span>
									{:else}
										<span class="func-pill muted-pill">Rolling context</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else if activeTab === 'specs'}
			<div class="specs-grid">
				<div class="spec-card">
					<div class="spec-card-head">
						<h3 class="spec-card-title">Physical asset limits</h3>
					</div>
					<div class="spec-rows font-mono">
						<div class="spec-item">
							<span class="spec-lbl">PV Inverter ceiling</span>
							<span class="spec-val pv-text">50.0 kW</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Peak building demand</span>
							<span class="spec-val load-text">45.0 kW</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Overnight baseline demand</span>
							<span class="spec-val">10.0 kW</span>
						</div>
					</div>
				</div>

				<div class="spec-card">
					<div class="spec-card-head">
						<h3 class="spec-card-title">Model architecture</h3>
					</div>
					<div class="spec-rows font-mono">
						<div class="spec-item">
							<span class="spec-lbl">Model type</span>
							<span class="spec-val">Dual LightGBM Regressors</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Conditioning</span>
							<span class="spec-val">Horizon index h ∈ [1..24]</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Tree budget</span>
							<span class="spec-val">150 trees, max depth 6</span>
						</div>
					</div>
				</div>

				<div class="spec-card">
					<div class="spec-card-head">
						<h3 class="spec-card-title">Accuracy benchmarks</h3>
					</div>
					<div class="spec-rows font-mono">
						<div class="spec-item">
							<span class="spec-lbl">PV Daylight error</span>
							<span class="spec-val surplus-text">0.26% nMAE (Limit ≤ 5.0%)</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Load 24h error</span>
							<span class="spec-val surplus-text">2.99% nMAE (Limit ≤ 6.0%)</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Variance explained (R²)</span>
							<span class="spec-val surplus-text">&gt; 0.93 (Target ≥ 0.85)</span>
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="params-grid">
				<div class="param-box">
					<span class="param-category font-mono">Control input</span>
					<h3 class="param-name">Forecast origin (Time T)</h3>
					<p class="param-description">The reference time hour. Past sensor data locks at time T. The models project forward for hours T+1 to T+24.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Weather input</span>
					<h3 class="param-name">Solar irradiance (GHI)</h3>
					<p class="param-description">Solar power per square meter (W/m²). Dictates panel electricity generation. Strictly 0.0 W/m² at night.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Weather input</span>
					<h3 class="param-name">Outdoor temperature (°C)</h3>
					<p class="param-description">Ambient air temperature. Drives facility cooling demand and slightly reduces solar panel efficiency when hot.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Model output</span>
					<h3 class="param-name">Solar PV generation (P_pv)</h3>
					<p class="param-description">Predicted solar power in kilowatts (kW). Limited by the 50.0 kW inverter cap and set to 0.0 kW at night.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Model output</span>
					<h3 class="param-name">Building power demand (P_load)</h3>
					<p class="param-description">Predicted facility electricity consumption between 10.0 kW baseline and 45.0 kW peak.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Energy schedule</span>
					<h3 class="param-name">Net battery storage balance</h3>
					<p class="param-description">Net Power = Solar minus Load. Positive extra solar charges the battery. Negative power discharges the battery.</p>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.drawer-panel {
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	/* Segmented tab track */
	.drawer-tabs {
		display: flex;
		align-items: center;
		gap: 2px;
		width: fit-content;
		max-width: calc(100% - 4rem);
		margin: 1.5rem 2rem 0;
		padding: 3px;
		background: var(--surface-sunken);
		border-radius: 999px;
		overflow-x: auto;
		scrollbar-width: none;
	}

	.drawer-tabs::-webkit-scrollbar {
		display: none;
	}

	.tab-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		height: 34px;
		padding: 0 1rem;
		background: transparent;
		color: var(--text-secondary);
		font-family: var(--font-sans);
		font-size: 0.78rem;
		font-weight: 500;
		line-height: 1;
		white-space: nowrap;
		border-radius: 999px;
		cursor: pointer;
		border: none;
		transition: all 0.3s var(--ease);
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		background: var(--surface);
		color: var(--text-primary);
		box-shadow:
			0 0 0 1px var(--hairline),
			0 2px 6px -2px rgba(23, 21, 15, 0.16);
	}

	.drawer-body {
		padding: 1.5rem 2rem 2rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	/* Explainer Banner */
	.tab-explainer {
		background: var(--surface-soft);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 0.85rem 1.1rem;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		font-size: 0.76rem;
		color: var(--text-secondary);
	}

	.tab-explainer p {
		margin: 0;
		line-height: 1.5;
	}

	.tab-explainer strong {
		color: var(--text-primary);
	}

	.explainer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.explainer-tag {
		font-size: 0.65rem;
		font-weight: 700;
		letter-spacing: 0.06em;
		color: var(--text-muted);
	}

	.highlight-tag {
		color: var(--color-load-ink);
	}

	.explainer-note {
		font-size: 0.68rem;
		color: var(--text-muted);
	}

	.lag-banner {
		background: rgba(2, 132, 199, 0.05);
		border-color: rgba(2, 132, 199, 0.2);
	}

	.table-container {
		max-height: 380px;
		overflow-y: auto;
		border-radius: var(--radius-inner);
		box-shadow: inset 0 0 0 1px var(--hairline);
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
		font-size: 0.78rem;
	}

	.data-table th {
		background: var(--surface-soft);
		color: var(--text-muted);
		padding: 0.8rem 1rem;
		font-family: var(--font-sans);
		font-size: 0.66rem;
		font-weight: 500;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		white-space: nowrap;
		border-bottom: 1px solid var(--hairline);
		position: sticky;
		top: 0;
		z-index: 2;
	}

	.data-table td {
		padding: 0.7rem 1rem;
		border-bottom: 1px solid var(--hairline);
		color: var(--text-secondary);
		white-space: nowrap;
	}

	.data-table tr:last-child td {
		border-bottom: none;
	}

	.data-table tbody tr {
		transition: background-color 0.3s var(--ease);
	}

	.data-table tbody tr:hover {
		background: var(--surface-soft);
	}

	.highlight-row {
		background: rgba(255, 255, 255, 0.02);
	}

	.horizon-cell {
		color: var(--text-primary) !important;
		font-weight: 500;
	}

	.time-cell {
		color: var(--text-muted) !important;
	}

	.pv-text {
		color: var(--color-pv-ink) !important;
	}

	.load-text {
		color: var(--color-load-ink) !important;
	}

	.surplus-text {
		color: var(--color-surplus-ink);
	}

	/* Anchor badges */
	.anchor-badge {
		display: inline-block;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		font-weight: 700;
		font-size: 0.72rem;
	}

	.origin-badge {
		background: rgba(2, 132, 199, 0.2);
		color: var(--color-load-ink);
		border: 1px solid rgba(2, 132, 199, 0.4);
	}

	.momentum-badge {
		background: rgba(232, 137, 12, 0.15);
		color: var(--color-pv-ink);
		border: 1px solid rgba(232, 137, 12, 0.3);
	}

	.baseline-badge {
		background: rgba(99, 102, 241, 0.15);
		color: #a5b4fc;
		border: 1px solid rgba(99, 102, 241, 0.3);
	}

	/* Function pills */
	.func-pill {
		display: inline-flex;
		align-items: center;
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		font-size: 0.68rem;
		background: var(--surface-sunken);
		color: var(--text-secondary);
	}

	.origin-pill {
		background: rgba(2, 132, 199, 0.15);
		color: var(--color-load-ink);
		font-weight: 600;
	}

	.momentum-pill {
		background: rgba(232, 137, 12, 0.15);
		color: var(--color-pv-ink);
	}

	.baseline-pill {
		background: rgba(99, 102, 241, 0.15);
		color: #a5b4fc;
	}

	.muted-pill {
		color: var(--text-muted);
		opacity: 0.7;
	}

	.cell-with-bar {
		display: flex;
		align-items: center;
		gap: 0.85rem;
	}

	.bar-track {
		width: 56px;
		height: 4px;
		background: var(--surface-sunken);
		border-radius: 999px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: 999px;
	}

	.pv-fill {
		background: var(--color-pv);
	}

	.cloud-fill {
		background: rgba(255, 244, 225, 0.28);
	}

	.status-tag {
		display: inline-flex;
		font-family: var(--font-sans);
		font-size: 0.7rem;
		font-weight: 500;
		padding: 0.15rem 0.65rem;
		border-radius: 999px;
	}

	.status-tag.daylight {
		color: var(--color-pv-ink);
		background: var(--color-pv-muted);
	}

	.status-tag.night {
		color: var(--text-muted);
		background: var(--surface-sunken);
	}

	/* Specs & Params Grid */
	.specs-grid,
	.params-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.25rem;
	}

	.spec-card,
	.param-box {
		background: var(--surface-soft);
		box-shadow: inset 0 0 0 1px var(--hairline);
		border-radius: 18px;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
	}

	.spec-card {
		gap: 1.1rem;
	}

	.spec-card-title,
	.param-name {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 600;
		letter-spacing: -0.01em;
		color: var(--text-primary);
	}

	.spec-rows {
		display: flex;
		flex-direction: column;
		font-size: 0.78rem;
	}

	.spec-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		padding: 0.65rem 0;
		border-top: 1px solid var(--hairline);
	}

	.spec-lbl {
		font-family: var(--font-sans);
		color: var(--text-muted);
	}

	.spec-val {
		color: var(--text-primary);
		font-weight: 500;
	}

	.param-box {
		gap: 0.6rem;
	}

	.param-category {
		font-size: 0.66rem;
		color: var(--color-load-ink);
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.param-description {
		margin: 0;
		font-size: 0.78rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	@media (max-width: 760px) {
		.drawer-tabs {
			margin: 1.25rem 1.25rem 0;
			max-width: calc(100% - 2.5rem);
		}

		.drawer-body {
			padding: 1.25rem;
		}
	}
</style>
