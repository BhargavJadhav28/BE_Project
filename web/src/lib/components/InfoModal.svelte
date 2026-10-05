<script lang="ts">
	import { Lock, CheckCircle2, XCircle, X } from '@lucide/svelte';

	interface Props {
		isOpen: boolean;
		onClose: () => void;
	}

	let { isOpen = false, onClose }: Props = $props();

	type TabId = 'workflow' | 'lags' | 'inputs' | 'glossary';
	let activeTab = $state<TabId>('workflow');

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && isOpen) {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
	<div class="modal-backdrop" onclick={onClose} role="presentation">
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="modal-window"
			role="dialog"
			aria-modal="true"
			tabindex="-1"
			aria-labelledby="modal-title"
			onclick={(e) => e.stopPropagation()}
		>
			<!-- Header -->
			<div class="modal-header">
				<div>
					<h2 id="modal-title" class="modal-title">System architecture & intuitive guide</h2>
					<p class="modal-subtitle">Autonomous 24-hour microgrid forecasting and battery dispatch specifications</p>
				</div>
				<button class="close-btn" onclick={onClose} aria-label="Close guide">
					✕
				</button>
			</div>

			<!-- Tabs -->
			<div class="modal-tabs">
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'workflow'}
					onclick={() => (activeTab = 'workflow')}
				>Pipeline Workflow</button>
				<button
					class="tab-btn font-mono highlight-tab"
					class:active={activeTab === 'lags'}
					onclick={() => (activeTab = 'lags')}
				>How Lags Work (ADR 0001)</button>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'inputs'}
					onclick={() => (activeTab = 'inputs')}
					>Feeds & Controls</button
				>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'glossary'}
					onclick={() => (activeTab = 'glossary')}
				>ASD-STE100 Glossary</button>
			</div>

			<!-- Body -->
			<div class="modal-body">
				{#if activeTab === 'workflow'}
					<div class="tab-pane">
						<div class="callout-box">
							<span class="callout-tag font-mono">CORE ARCHITECTURAL PRINCIPLE (ADR 0001)</span>
							<h3>Predict All 24 Hours in One Step</h3>
							<p>Helios uses horizon conditioning instead of step-by-step recursion. The models predict all 24 future hours simultaneously in under 25 milliseconds. This eliminates compounding prediction errors.</p>
						</div>

						<div class="workflow-steps">
							<div class="workflow-step">
								<span class="step-num font-mono">01</span>
								<div class="step-text">
									<h4>Clean sensor data (Sanitizer)</h4>
									<p>Collect 48 hours of rolling sensor logs. Automatically fill missing values for gaps of 3 hours or less. If a gap exceeds 3 hours, stop and signal an alarm.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">02</span>
								<div class="step-text">
									<h4>Lock origin and feature lags</h4>
									<p>Lock all sensor measurements at time T. The model cannot read future data. Combine past measurements with 24-hour weather predictions.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">03</span>
								<div class="step-text">
									<h4>Infer power with dual LightGBM</h4>
									<p>Run two specialized gradient-boosted models in parallel: one for Solar PV and one for Building Load. Predict all 24 hours at once.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">04</span>
								<div class="step-text">
									<h4>Enforce physical limits</h4>
									<p>Set solar power to 0.0 kW when the sun is down. Clip solar generation to the 50.0 kW inverter ceiling. Bound facility load between 10.0 kW and 45.0 kW.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">05</span>
								<div class="step-text">
									<h4>Schedule battery storage</h4>
									<p>Calculate Net Power = Solar minus Load. When solar power exceeds load, charge the battery. When load exceeds solar power, discharge the battery to reduce grid cost.</p>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'lags'}
					<!-- SPECIFIC DEDICATED SECTION FOR HOW LAGS WORK -->
					<div class="tab-pane">
						<div class="callout-box lag-focus">
							<span class="callout-tag font-mono">EXPLAINING TIME-SERIES LAGS</span>
							<h3>What Is a Lag and Why Does It Matter?</h3>
							<p>A <strong>lag</strong> is a sensor measurement from a specific time in the past. In electrical power systems, power consumption and solar production repeat in daily 24-hour cycles. Past measurements are the strongest predictor of tomorrow's energy.</p>
						</div>

						<!-- Visual Lag Diagram Card -->
						<div class="lag-graphic-card font-mono">
							<div class="graphic-title">THE ORIGIN FREEZE ARCHITECTURE (ADR 0001)</div>
							
							<div class="graphic-timeline">
								<div class="timeline-zone past-zone">
									<span class="zone-label">PAST SENSOR LOGS</span>
									<div class="zone-pills">
										<div class="zone-pill">
											<strong>T - 24h</strong>
											<span>Yesterday's power at this exact hour (Daily Baseline)</span>
										</div>
										<div class="zone-pill">
											<strong>T - 6h..T</strong>
											<span>Rolling 6-hour power mean (Recent energy trend)</span>
										</div>
										<div class="zone-pill">
											<strong>T - 1h</strong>
											<span>Power 1 hour ago (Immediate momentum ramp)</span>
										</div>
										<div class="zone-pill origin-pill-graphic">
											<strong>Time T</strong>
											<span>Power right now (Anchor moment)</span>
										</div>
									</div>
								</div>

								<div class="timeline-barrier">
									<div class="barrier-line"></div>
									<div class="barrier-badge">
										<Lock size={12} class="text-sky" />
										<span>TIME T LOCK</span>
									</div>
									<div class="barrier-line"></div>
								</div>

								<div class="timeline-zone future-zone">
									<span class="zone-label">FUTURE FORECAST HORIZON</span>
									<div class="horizon-preview">
										<div class="h-step">T+1h</div>
										<div class="h-step">T+2h</div>
										<div class="h-step">...</div>
										<div class="h-step">T+24h</div>
									</div>
									<p class="zone-desc">The model evaluates all 24 horizons using the <em>exact same frozen lags</em> from time T plus forward weather forecasts.</p>
								</div>
							</div>
						</div>

						<!-- Two Approaches Comparison -->
						<div class="comparison-grid">
							<div class="comp-box bad-box">
								<h4 class="comp-title font-mono">
									<XCircle size={15} class="text-rose" />
									<span>Naive Recursive Method (Why it fails)</span>
								</h4>
								<ul class="comp-list">
									<li>To predict hour 2, it feeds its own prediction from hour 1 back in as a "lag".</li>
									<li>To predict hour 24, small errors multiply 24 times.</li>
									<li>Causes huge prediction drift and unstable energy dispatch.</li>
								</ul>
							</div>

							<div class="comp-box good-box">
								<h4 class="comp-title font-mono">
									<CheckCircle2 size={15} class="text-emerald" />
									<span>Helios Origin-Conditioned Method (Our system)</span>
								</h4>
								<ul class="comp-list">
									<li>Locks all historical lags strictly at origin moment T.</li>
									<li>Conditions directly on the horizon index (step h from 1 to 24).</li>
									<li>Zero error multiplication. Zero data leakage. 25 ms inference.</li>
								</ul>
							</div>
						</div>
					</div>

				{:else if activeTab === 'inputs'}
					<div class="tab-pane">
						<div class="split-columns">
							<div class="col-panel">
								<h3>Operator Controls</h3>
								<div class="feed-list">
									<div class="feed-item">
										<strong>Forecast origin (Time T)</strong>
										<p>The anchor hour. Historical sensor data spans [T-48h to T]. Predictions project [T+1h to T+24h].</p>
									</div>
									<div class="feed-item">
										<strong>Scenario profiles</strong>
										<p>Pre-configured seasonal profiles (Summer peak, Winter evening, Spring ramp, Storm front) to test microgrid performance.</p>
									</div>
									<div class="feed-item">
										<strong>Sensor gap stress test</strong>
										<p>Simulates lost communication signals to verify automated linear healing and supervisory alarm trips.</p>
									</div>
								</div>
							</div>

							<div class="col-panel">
								<h3>Automated Sensor & Weather Feeds</h3>
								<div class="feed-list">
									<div class="feed-item">
										<strong>48-Hour sensor buffer</strong>
										<p>Continuous logs of solar panel output (kW), building power demand (kW), outdoor temperature (°C), and solar irradiance (W/m²).</p>
									</div>
									<div class="feed-item">
										<strong>24-Hour numerical weather forecast</strong>
										<p>Forward numerical predictions of solar irradiance (GHI), ambient temperature (°C), and cloud cover (%).</p>
									</div>
									<div class="feed-item">
										<strong>Calendar encodings</strong>
										<p>Hour-of-day and day-of-year cyclical variables to capture facility work shifts and seasonal daylight changes.</p>
									</div>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'glossary'}
					<div class="tab-pane">
						<div class="table-container font-mono">
							<table class="glossary-table">
								<thead>
									<tr>
										<th>Term</th>
										<th>Unit</th>
										<th>Category</th>
										<th>Operational Definition & Rule</th>
									</tr>
								</thead>
								<tbody>
									<tr>
										<td><strong>Lag</strong></td>
										<td>Index</td>
										<td>Feature</td>
										<td>Sensor measurement from the past (e.g., T-1h, T-24h). Locked at origin T.</td>
									</tr>
									<tr>
										<td><strong>Origin (Time T)</strong></td>
										<td>Timestamp</td>
										<td>Control</td>
										<td>The forecast reference hour. Divides past observations from future predictions.</td>
									</tr>
									<tr>
										<td><strong>kW (Kilowatt)</strong></td>
										<td>Power</td>
										<td>Rate</td>
										<td>Instantaneous rate of electricity generated or consumed at a single moment.</td>
									</tr>
									<tr>
										<td><strong>kWh (Kilowatt-hour)</strong></td>
										<td>Energy</td>
										<td>Volume</td>
										<td>Accumulated volume of electricity over time (1 kW sustained for 1 hour = 1 kWh).</td>
									</tr>
									<tr>
										<td><strong>Solar PV (P_pv)</strong></td>
										<td>kW</td>
										<td>Asset</td>
										<td>Photovoltaic solar generation. Limited to 50.0 kW inverter cap; 0.0 kW at night.</td>
									</tr>
									<tr>
										<td><strong>Building Load (P_load)</strong></td>
										<td>kW</td>
										<td>Asset</td>
										<td>Facility electricity consumption. Baseline: 10.0 kW; Peak capacity: 45.0 kW.</td>
									</tr>
									<tr>
										<td><strong>GHI (Solar Irradiance)</strong></td>
										<td>W/m²</td>
										<td>Weather</td>
										<td>Global Horizontal Irradiance: solar power per square meter. 0.0 W/m² at night.</td>
									</tr>
									<tr>
										<td><strong>nMAE Error</strong></td>
										<td>%</td>
										<td>Accuracy</td>
										<td>Capacity-Normalized Mean Absolute Error. PV error: 0.26%; Load error: 2.99%.</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="modal-footer">
				<button class="return-btn" onclick={onClose}>
					Close guide
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes pop-in {
		from {
			opacity: 0;
			transform: translateY(14px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.72);
		backdrop-filter: blur(14px);
		-webkit-backdrop-filter: blur(14px);
		z-index: 1000;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1.5rem;
		animation: fade-in 0.4s var(--ease) both;
	}

	.modal-window {
		background: var(--surface);
		border-radius: 28px;
		width: 100%;
		max-width: 860px;
		max-height: 88dvh;
		display: flex;
		flex-direction: column;
		box-shadow:
			0 0 0 1px var(--hairline-strong),
			0 40px 80px -20px rgba(0, 0, 0, 0.9);
		overflow: hidden;
		animation: pop-in 0.6s var(--ease) both;
	}

	.modal-header {
		padding: 1.75rem 2rem 1.25rem;
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}

	.modal-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: 1.85rem;
		font-weight: 400;
		line-height: 1.1;
		letter-spacing: -0.015em;
		color: var(--text-primary);
	}

	.modal-subtitle {
		margin: 0.45rem 0 0;
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.close-btn {
		flex-shrink: 0;
		width: 34px;
		height: 34px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.25s var(--ease);
	}

	.close-btn:hover {
		color: var(--text-primary);
		background: var(--surface-soft);
	}

	.modal-tabs {
		display: flex;
		gap: 4px;
		padding: 0 2rem 1rem;
		border-bottom: 1px solid var(--hairline);
		overflow-x: auto;
	}

	.tab-btn {
		background: transparent;
		border: none;
		color: var(--text-muted);
		padding: 0.45rem 0.9rem;
		border-radius: 999px;
		font-size: 0.76rem;
		cursor: pointer;
		white-space: nowrap;
		transition: all 0.25s var(--ease);
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		background: var(--surface-sunken);
		color: var(--text-primary);
		font-weight: 600;
	}

	.tab-btn.highlight-tab.active {
		background: rgba(2, 132, 199, 0.15);
		color: var(--color-load-ink);
	}

	.modal-body {
		padding: 1.75rem 2rem;
		overflow-y: auto;
		flex: 1;
	}

	.tab-pane {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.callout-box {
		background: var(--surface-soft);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.callout-box.lag-focus {
		border-color: rgba(2, 132, 199, 0.3);
		background: rgba(2, 132, 199, 0.04);
	}

	.callout-tag {
		font-size: 0.65rem;
		color: var(--color-pv-ink);
		letter-spacing: 0.08em;
	}

	.lag-focus .callout-tag {
		color: var(--color-load-ink);
	}

	.callout-box h3 {
		margin: 0;
		font-size: 1.05rem;
		color: var(--text-primary);
	}

	.callout-box p {
		margin: 0;
		font-size: 0.82rem;
		line-height: 1.55;
		color: var(--text-secondary);
	}

	.workflow-steps {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.workflow-step {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		background: var(--surface-sunken);
		padding: 1rem 1.25rem;
		border-radius: var(--radius-inner);
		border: 1px solid var(--hairline);
	}

	.step-num {
		font-size: 0.72rem;
		font-weight: 700;
		color: var(--color-pv-ink);
		background: rgba(232, 137, 12, 0.1);
		padding: 0.25rem 0.55rem;
		border-radius: 6px;
	}

	.step-text {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.step-text h4 {
		margin: 0;
		font-size: 0.9rem;
		color: var(--text-primary);
	}

	.step-text p {
		margin: 0;
		font-size: 0.78rem;
		line-height: 1.5;
		color: var(--text-secondary);
	}

	/* Lag Graphic Card */
	.lag-graphic-card {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		border-radius: var(--radius-inner);
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.graphic-title {
		font-size: 0.7rem;
		font-weight: 700;
		color: var(--color-load-ink);
		letter-spacing: 0.08em;
	}

	.graphic-timeline {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: 1rem;
		align-items: center;
	}

	.timeline-zone {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}

	.zone-label {
		font-size: 0.65rem;
		color: var(--text-muted);
		letter-spacing: 0.05em;
	}

	.zone-pills {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.zone-pill {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--hairline);
		padding: 0.4rem 0.6rem;
		border-radius: 4px;
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		font-size: 0.68rem;
	}

	.zone-pill strong {
		color: var(--text-primary);
	}

	.zone-pill span {
		font-size: 0.62rem;
		color: var(--text-muted);
	}

	.origin-pill-graphic {
		border-color: rgba(2, 132, 199, 0.4);
		background: rgba(2, 132, 199, 0.1);
	}

	.origin-pill-graphic strong {
		color: var(--color-load-ink);
	}

	.timeline-barrier {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}

	.barrier-line {
		width: 1px;
		height: 40px;
		background: var(--hairline-strong);
	}

	.barrier-badge {
		font-size: 0.65rem;
		font-weight: 700;
		color: #eab308;
		background: rgba(234, 179, 8, 0.1);
		border: 1px solid rgba(234, 179, 8, 0.3);
		padding: 0.3rem 0.6rem;
		border-radius: 999px;
		white-space: nowrap;
	}

	.horizon-preview {
		display: flex;
		gap: 0.4rem;
		flex-wrap: wrap;
	}

	.h-step {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--hairline);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-size: 0.68rem;
		color: var(--text-secondary);
	}

	.zone-desc {
		font-size: 0.72rem;
		color: var(--text-secondary);
		line-height: 1.45;
		margin: 0;
	}

	/* Comparison Grid */
	.comparison-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.comp-box {
		padding: 1rem;
		border-radius: var(--radius-inner);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.bad-box {
		background: rgba(224, 54, 95, 0.04);
		border: 1px solid rgba(224, 54, 95, 0.2);
	}

	.bad-box .comp-title {
		color: var(--color-deficit-ink);
	}

	.good-box {
		background: rgba(18, 160, 113, 0.04);
		border: 1px solid rgba(18, 160, 113, 0.2);
	}

	.good-box .comp-title {
		color: var(--color-surplus-ink);
	}

	.comp-title {
		margin: 0;
		font-size: 0.8rem;
	}

	.comp-list {
		margin: 0;
		padding-left: 1.2rem;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		font-size: 0.74rem;
		color: var(--text-secondary);
		line-height: 1.4;
	}

	/* Split Columns in Inputs tab */
	.split-columns {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
	}

	.col-panel {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.col-panel h3 {
		margin: 0;
		font-size: 0.95rem;
		color: var(--text-primary);
	}

	.feed-list {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}

	.feed-item {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		font-size: 0.78rem;
	}

	.feed-item strong {
		color: var(--text-primary);
	}

	.feed-item p {
		margin: 0;
		color: var(--text-secondary);
		line-height: 1.45;
	}

	/* Glossary Table */
	.table-container {
		border-radius: var(--radius-inner);
		box-shadow: inset 0 0 0 1px var(--hairline);
		overflow-x: auto;
	}

	.glossary-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.76rem;
		text-align: left;
	}

	.glossary-table th {
		background: var(--surface-soft);
		color: var(--text-muted);
		padding: 0.75rem 1rem;
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		border-bottom: 1px solid var(--hairline);
	}

	.glossary-table td {
		padding: 0.7rem 1rem;
		border-bottom: 1px solid var(--hairline);
		color: var(--text-secondary);
	}

	.glossary-table tr:last-child td {
		border-bottom: none;
	}

	.modal-footer {
		padding: 1.25rem 2rem;
		border-top: 1px solid var(--hairline);
		display: flex;
		justify-content: flex-end;
	}

	.return-btn {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		color: var(--text-primary);
		padding: 0.5rem 1.25rem;
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.25s var(--ease);
	}

	.return-btn:hover {
		background: var(--surface-soft);
	}

	@media (max-width: 760px) {
		.graphic-timeline,
		.comparison-grid,
		.split-columns {
			grid-template-columns: 1fr;
		}

		.modal-window {
			max-height: 94dvh;
		}

		.modal-header,
		.modal-body,
		.modal-footer {
			padding-inline: 1.25rem;
		}
	}
</style>
