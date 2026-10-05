<script lang="ts">
	import type { WeatherForecastStep } from '../types';

	interface Props {
		timestamps: string[];
		pvForecast: number[];
		loadForecast: number[];
		weather: WeatherForecastStep[];
	}

	let { timestamps = [], pvForecast = [], loadForecast = [], weather = [] }: Props = $props();

	type ChartMode = 'all' | 'solar' | 'load';
	let chartMode = $state<ChartMode>('all');
	let hoveredIndex = $state<number | null>(null);
	let showGuide = $state(false);

	// Canvas dimensions
	const width = 1000;
	const height = 365;
	const padLeft = 56;
	const padRight = 32;
	const padTop = 32;
	const padBottom = 48;

	const chartW = width - padLeft - padRight;
	const chartH = height - padTop - padBottom;
	const maxKw = 55.0;

	function getX(index: number): number {
		if (timestamps.length <= 1) return padLeft;
		return padLeft + (index / (timestamps.length - 1)) * chartW;
	}

	function getY(kw: number): number {
		const clamped = Math.max(0, Math.min(maxKw, kw));
		return padTop + chartH - (clamped / maxKw) * chartH;
	}

	function buildLinePath(points: { x: number; y: number }[]): string {
		if (!points.length) return '';
		return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
	}

	let pvPoints = $derived(pvForecast.map((val, i) => ({ x: getX(i), y: getY(val) })));
	let loadPoints = $derived(loadForecast.map((val, i) => ({ x: getX(i), y: getY(val) })));

	let pvPath = $derived(buildLinePath(pvPoints));
	let loadPath = $derived(buildLinePath(loadPoints));

	let pvAreaPath = $derived.by(() => {
		if (!pvPoints.length) return '';
		const line = pvPath;
		const lastX = getX(pvForecast.length - 1);
		const firstX = getX(0);
		const baseY = getY(0);
		return `${line} L ${lastX.toFixed(1)} ${baseY.toFixed(1)} L ${firstX.toFixed(1)} ${baseY.toFixed(1)} Z`;
	});

	let loadAreaPath = $derived.by(() => {
		if (!loadPoints.length) return '';
		const line = loadPath;
		const lastX = getX(loadForecast.length - 1);
		const firstX = getX(0);
		const baseY = getY(0);
		return `${line} L ${lastX.toFixed(1)} ${baseY.toFixed(1)} L ${firstX.toFixed(1)} ${baseY.toFixed(1)} Z`;
	});

	let peakPv = $derived(pvForecast.length ? Math.max(...pvForecast) : 0);
	let peakLoad = $derived(loadForecast.length ? Math.max(...loadForecast) : 0);

	let hoveredNet = $derived(
		hoveredIndex !== null ? (pvForecast[hoveredIndex] || 0) - (loadForecast[hoveredIndex] || 0) : 0
	);

	const yGridTicks = [0, 10, 20, 30, 40, 50];

	function formatTime(iso: string): string {
		if (!iso) return '';
		// Extract direct wall-clock hour (HH:00) without timezone offset distortion
		if (iso.includes('T')) {
			const timePart = iso.split('T')[1];
			if (timePart && timePart.length >= 2) {
				return `${timePart.slice(0, 2)}:00`;
			}
		}
		try {
			const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
			const h = String(d.getUTCHours()).padStart(2, '0');
			return `${h}:00`;
		} catch {
			return '';
		}
	}

	function handleTouchMove(e: TouchEvent) {
		if (!e.touches.length || timestamps.length <= 1) return;
		const target = e.currentTarget as SVGSVGElement;
		const rect = target.getBoundingClientRect();
		const clientX = e.touches[0].clientX - rect.left;
		const normX = (clientX / rect.width) * width;
		const rawIdx = Math.round(((normX - padLeft) / chartW) * (timestamps.length - 1));
		hoveredIndex = Math.max(0, Math.min(timestamps.length - 1, rawIdx));
	}
</script>

<div class="chart-panel">
	<!-- Header Bar -->
	<div class="chart-header">
		<div>
			<h2 class="chart-title">24-hour power dispatch trajectory</h2>
			<p class="chart-subtitle">Discrete lookahead with 50 kW PV inverter limit, 45 kW load capacity, and battery arbitrage</p>
		</div>

		<div class="chart-actions">
			<div class="mode-selector font-mono">
				<button
					class="mode-btn"
					class:active={chartMode === 'all'}
					onclick={() => (chartMode = 'all')}
				>
					Combined
				</button>
				<button
					class="mode-btn"
					class:active={chartMode === 'solar'}
					onclick={() => (chartMode = 'solar')}
				>
					Solar PV
				</button>
				<button
					class="mode-btn"
					class:active={chartMode === 'load'}
					onclick={() => (chartMode = 'load')}
				>
					Load demand
				</button>
			</div>

			<button
				class="guide-btn font-mono"
				class:active={showGuide}
				onclick={() => (showGuide = !showGuide)}
			>
				{showGuide ? 'Hide guide' : 'View guide'}
			</button>
		</div>
	</div>

	{#if showGuide}
		<div class="guide-panel">
			<div class="guide-item">
				<span class="guide-label pv-label">
					<span class="guide-dot pv-dot"></span>
					Solar PV (Amber)
				</span>
				<p>Predicted photovoltaic output. Strictly zeroed when solar irradiance is zero (night) and clipped to the 50 kW inverter ceiling.</p>
			</div>
			<div class="guide-item">
				<span class="guide-label load-label">
					<span class="guide-dot load-dot"></span>
					Load demand (Sky blue)
				</span>
				<p>Facility power consumption conditioned on historical sensor telemetry, weekday rhythm, and ambient temperature.</p>
			</div>
			<div class="guide-item">
				<span class="guide-label net-label">
					<span class="guide-dot surplus-dot"></span>
					<span class="guide-dot deficit-dot"></span>
					Battery balance (Green / Red)
				</span>
				<p>Surplus generation (Green) charges battery storage. Deficit demand (Red) triggers economic battery discharge or grid import.</p>
			</div>
		</div>
	{/if}

	<!-- Telemetry Inspector Bar -->
	<div class="telemetry-bar font-mono">
		{#if hoveredIndex !== null && timestamps[hoveredIndex]}
			{@const hGhi = weather[hoveredIndex]?.ghi ?? 0}
			{@const hTemp = weather[hoveredIndex]?.temp_amb ?? 0}
			{@const hCloud = weather[hoveredIndex]?.cloud_cover ?? 0}
			<div class="telemetry-stat">
				<span class="stat-name">Horizon:</span>
				<span class="stat-val highlight">T+{hoveredIndex + 1} ({formatTime(timestamps[hoveredIndex])})</span>
			</div>
			<div class="telemetry-stat">
				<span class="stat-name">Solar:</span>
				<span class="stat-val pv-val">{pvForecast[hoveredIndex]?.toFixed(1)} kW</span>
			</div>
			<div class="telemetry-stat">
				<span class="stat-name">Load:</span>
				<span class="stat-val load-val">{loadForecast[hoveredIndex]?.toFixed(1)} kW</span>
			</div>
			<div class="telemetry-stat">
				<span class="stat-name">Net:</span>
				<span class="stat-val" class:surplus={hoveredNet >= 0} class:deficit={hoveredNet < 0}>
					{hoveredNet >= 0 ? '+' : ''}{hoveredNet.toFixed(1)} kW
					<span class="net-pill" class:surplus-pill={hoveredNet >= 0} class:deficit-pill={hoveredNet < 0}>
						{hoveredNet >= 0 ? 'Charging storage' : 'Discharging storage'}
					</span>
				</span>
			</div>
			<div class="telemetry-stat weather-stat">
				<span class="stat-name">Weather:</span>
				<span class="stat-val muted">{hGhi.toFixed(0)} W/m², {hTemp.toFixed(1)}°C, {hCloud.toFixed(0)}% cloud</span>
			</div>
		{:else}
			<div class="telemetry-idle">
				<span>Hover or scrub along the timeline to inspect hourly generation, load demand, and battery storage balance</span>
				<div class="chart-legend font-mono">
					<span class="legend-item"><span class="legend-pip pv-pip"></span>Solar PV</span>
					<span class="legend-item"><span class="legend-pip load-pip"></span>Building load</span>
					<span class="legend-item"><span class="legend-pip surplus-pip"></span>Surplus (Charging)</span>
					<span class="legend-item"><span class="legend-pip deficit-pip"></span>Deficit (Discharging)</span>
				</div>
			</div>
		{/if}
	</div>

	<!-- SVG Canvas -->
	<div class="svg-wrap">
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<svg
			viewBox="0 0 {width} {height}"
			class="chart-svg"
			onmouseleave={() => (hoveredIndex = null)}
			ontouchstart={handleTouchMove}
			ontouchmove={handleTouchMove}
			ontouchend={() => (hoveredIndex = null)}
		>
			<defs>
				<!-- Solar Amber Area Fade -->
				<linearGradient id="pvFillAmber" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0%" stop-color="#E8890C" stop-opacity="0.22" />
					<stop offset="100%" stop-color="#E8890C" stop-opacity="0.0" />
				</linearGradient>

				<!-- Sky Blue Area Fade -->
				<linearGradient id="loadFillSky" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0%" stop-color="#2D84D6" stop-opacity="0.14" />
					<stop offset="100%" stop-color="#2D84D6" stop-opacity="0.0" />
				</linearGradient>

				<!-- Chart Area Clip to Prevent Edge Bleed -->
				<clipPath id="chartAreaClip">
					<rect x={padLeft} y={padTop} width={chartW} height={chartH} />
				</clipPath>
			</defs>

			<!-- Nocturnal Shaded Bands -->
			<g clip-path="url(#chartAreaClip)">
				{#each weather as step, i}
					{@const x = getX(i)}
					{@const w = chartW / (timestamps.length - 1)}
					{#if step.ghi <= 0}
						<rect
							x={x - w / 2}
							y={padTop}
							width={w}
							height={chartH}
							fill="#17150F"
							opacity="0.05"
						/>
					{/if}
				{/each}
			</g>

			<!-- Grid Lines -->
			{#each yGridTicks as tick}
				{@const yPos = getY(tick)}
				<line
					x1={padLeft}
					y1={yPos}
					x2={width - padRight}
					y2={yPos}
					class="grid-line"
				/>
				<text
					x={padLeft - 10}
					y={yPos + 4}
					class="axis-text y-axis font-mono"
				>
					{tick} kW
				</text>
			{/each}

			<!-- Inverter 50 kW Line -->
			<line
				x1={padLeft}
				y1={getY(50)}
				x2={width - padRight}
				y2={getY(50)}
				class="limit-line pv-limit"
			/>
			<text
				x={width - padRight - 8}
				y={getY(50) - 6}
				class="limit-label font-mono pv-val"
			>
				50 kW inverter ceiling
			</text>

			<!-- Peak Load 45 kW Line -->
			<line
				x1={padLeft}
				y1={getY(45)}
				x2={width - padRight}
				y2={getY(45)}
				class="limit-line load-limit"
			/>
			<text
				x={width - padRight - 8}
				y={getY(45) + 12}
				class="limit-label font-mono load-val"
			>
				45 kW peak load capacity
			</text>

			<!-- Solar Area -->
			{#if pvAreaPath && (chartMode === 'all' || chartMode === 'solar')}
				<path d={pvAreaPath} fill="url(#pvFillAmber)" />
			{/if}

			<!-- Load Area -->
			{#if loadAreaPath && (chartMode === 'all' || chartMode === 'load')}
				<path d={loadAreaPath} fill="url(#loadFillSky)" />
			{/if}

			<!-- Solar Line (Crisp Amber) -->
			{#if pvPath && (chartMode === 'all' || chartMode === 'solar')}
				<path
					d={pvPath}
					fill="none"
					stroke="#E8890C"
					stroke-width="2.2"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
			{/if}

			<!-- Load Line (Crisp Sky Blue) -->
			{#if loadPath && (chartMode === 'all' || chartMode === 'load')}
				<path
					d={loadPath}
					fill="none"
					stroke="#2D84D6"
					stroke-width="1.8"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
			{/if}

			<!-- 24-Hour Net Balance Status Ribbon (Emerald for Surplus, Rose for Deficit) -->
			{#if chartMode === 'all'}
				<g class="net-ribbon">
					{#each timestamps as _, i}
						{@const x = getX(i)}
						{@const w = Math.max(2, (chartW / (timestamps.length - 1)) * 0.72)}
						{@const stepNet = (pvForecast[i] || 0) - (loadForecast[i] || 0)}
						{@const isSurplus = stepNet >= 0}
						<rect
							x={x - w / 2}
							y={padTop + chartH + 4}
							width={w}
							height={4}
							rx={2}
							fill={isSurplus ? '#12A071' : '#E0365F'}
							opacity={hoveredIndex === i ? 1 : 0.65}
						/>
					{/each}
				</g>
			{/if}

			<!-- Hover Delta Connector (Shows live arbitrage delta) -->
			{#if hoveredIndex !== null}
				{@const curX = getX(hoveredIndex)}
				{@const curPvY = getY(pvForecast[hoveredIndex] || 0)}
				{@const curLoadY = getY(loadForecast[hoveredIndex] || 0)}
				{@const isSurplus = hoveredNet >= 0}
				
				<!-- Delta bar between curves -->
				<line
					x1={curX}
					y1={Math.min(curPvY, curLoadY)}
					x2={curX}
					y2={Math.max(curPvY, curLoadY)}
					stroke={isSurplus ? '#12A071' : '#E0365F'}
					stroke-width="2.5"
					stroke-linecap="round"
					opacity="0.9"
				/>
			{/if}

			<!-- Points & Interactive Hit Columns -->
			{#each timestamps as _, i}
				{@const x = getX(i)}
				{@const pvY = getY(pvForecast[i] || 0)}
				{@const loadY = getY(loadForecast[i] || 0)}

				{#if chartMode !== 'load'}
					<circle
						cx={x}
						cy={pvY}
						r={hoveredIndex === i ? 4.5 : 2}
						class="point-pv"
						class:active={hoveredIndex === i}
					/>
				{/if}

				{#if chartMode !== 'solar'}
					<circle
						cx={x}
						cy={loadY}
						r={hoveredIndex === i ? 4.5 : 2}
						class="point-load"
						class:active={hoveredIndex === i}
					/>
				{/if}

				<!-- X-Axis Labels: Harmonic 3-hour intervals ending cleanly on T+24 -->
				{#if (i + 1) % 3 === 0}
					<text
						x={x}
						y={height - 20}
						class="axis-text font-mono"
						text-anchor="middle"
					>
						{formatTime(timestamps[i])}
					</text>
					<text
						x={x}
						y={height - 6}
						class="axis-sub font-mono"
						text-anchor="middle"
					>
						T+{i + 1}
					</text>
				{/if}

				<!-- Hit Column -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<rect
					x={x - (chartW / (timestamps.length - 1)) / 2}
					y={padTop}
					width={chartW / (timestamps.length - 1)}
					height={chartH + 12}
					fill="transparent"
					class="hit-column"
					onmouseenter={() => (hoveredIndex = i)}
				/>
			{/each}

			<!-- Cursor Guide -->
			{#if hoveredIndex !== null}
				{@const curX = getX(hoveredIndex)}
				<line
					x1={curX}
					y1={padTop}
					x2={curX}
					y2={padTop + chartH + 8}
					class="cursor-guide"
				/>
			{/if}
		</svg>
	</div>
</div>

<style>
	.chart-panel {
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	.chart-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		padding: 1.75rem 2rem 1.5rem;
		flex-wrap: wrap;
		gap: 1rem 1.5rem;
	}

	.chart-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: 1.85rem;
		font-weight: 400;
		line-height: 1.1;
		letter-spacing: -0.015em;
		color: var(--text-primary);
	}

	.chart-subtitle {
		margin: 0.45rem 0 0;
		font-size: 0.85rem;
		color: var(--text-muted);
		max-width: 56ch;
		line-height: 1.5;
	}

	.chart-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.mode-selector {
		display: inline-flex;
		background: var(--surface-sunken);
		border-radius: 999px;
		padding: 3px;
		gap: 2px;
	}

	.mode-btn {
		font-family: var(--font-sans);
		background: transparent;
		color: var(--text-secondary);
		padding: 0.45rem 0.95rem;
		font-size: 0.78rem;
		font-weight: 500;
		border-radius: 999px;
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			box-shadow 0.4s var(--ease);
	}

	.mode-btn:hover {
		color: var(--text-primary);
	}

	.mode-btn.active {
		background: var(--surface);
		color: var(--text-primary);
		box-shadow:
			0 0 0 1px var(--hairline),
			0 2px 6px -2px rgba(23, 21, 15, 0.16);
	}

	.guide-btn {
		font-family: var(--font-sans);
		color: var(--text-secondary);
		padding: 0.5rem 1rem;
		font-size: 0.78rem;
		font-weight: 500;
		border-radius: 999px;
		box-shadow: inset 0 0 0 1px var(--hairline-strong);
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			transform 0.5s var(--ease);
	}

	.guide-btn:hover,
	.guide-btn.active {
		color: var(--text-primary);
		background: var(--surface-sunken);
	}

	.guide-btn:active {
		transform: scale(0.98);
	}

	.guide-panel {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1.5rem;
		padding: 1.5rem 2rem;
		background: var(--surface-soft);
		border-block: 1px solid var(--hairline);
	}

	.guide-item {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.guide-label {
		font-size: 0.8rem;
		font-weight: 600;
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}

	.guide-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
	}

	.pv-dot {
		background: var(--color-pv);
	}

	.load-dot {
		background: var(--color-load);
	}

	.surplus-dot {
		background: var(--color-surplus);
	}

	.deficit-dot {
		background: var(--color-deficit);
	}

	.guide-item p {
		margin: 0;
		font-size: 0.78rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	.pv-label {
		color: var(--color-pv-ink);
	}

	.load-label {
		color: var(--color-load-ink);
	}

	.net-label {
		color: var(--text-primary);
	}

	/* Telemetry inspector strip */
	.telemetry-bar {
		padding: 0.85rem 2rem;
		background: var(--surface-soft);
		border-block: 1px solid var(--hairline);
		display: flex;
		align-items: center;
		gap: 0.75rem 2rem;
		font-family: var(--font-sans);
		font-size: 0.78rem;
		flex-wrap: wrap;
		min-height: 52px;
	}

	.guide-panel + .telemetry-bar {
		border-top: none;
	}

	.telemetry-stat {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.stat-name {
		color: var(--text-muted);
		font-size: 0.74rem;
	}

	.stat-val {
		font-family: var(--font-mono);
		font-weight: 500;
		color: var(--text-primary);
	}

	.pv-val {
		color: var(--color-pv-ink);
	}

	.load-val {
		color: var(--color-load-ink);
	}

	.stat-val.surplus {
		color: var(--color-surplus-ink);
	}

	.stat-val.deficit {
		color: var(--color-deficit-ink);
	}

	.net-pill {
		display: inline-flex;
		align-items: center;
		padding: 0.15rem 0.6rem;
		border-radius: 999px;
		font-family: var(--font-sans);
		font-size: 0.68rem;
		font-weight: 500;
		margin-left: 0.5rem;
	}

	.surplus-pill {
		background: var(--color-surplus-muted);
		color: var(--color-surplus-ink);
	}

	.deficit-pill {
		background: var(--color-deficit-muted);
		color: var(--color-deficit-ink);
	}

	.muted {
		color: var(--text-muted);
	}

	.telemetry-idle {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		color: var(--text-muted);
		font-size: 0.78rem;
		flex-wrap: wrap;
		gap: 0.75rem 1.5rem;
	}

	.chart-legend {
		display: flex;
		align-items: center;
		gap: 0.5rem 1.25rem;
		flex-wrap: wrap;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		font-family: var(--font-sans);
		font-size: 0.74rem;
		color: var(--text-secondary);
	}

	.legend-pip {
		width: 7px;
		height: 7px;
		border-radius: 50%;
	}

	.pv-pip {
		background: var(--color-pv);
	}

	.load-pip {
		background: var(--color-load);
	}

	.surplus-pip {
		background: var(--color-surplus);
	}

	.deficit-pip {
		background: var(--color-deficit);
	}

	/* SVG canvas */
	.svg-wrap {
		width: 100%;
		overflow-x: auto;
		padding: 0.75rem 0.75rem 0.5rem;
	}

	.chart-svg {
		width: 100%;
		height: auto;
		display: block;
		user-select: none;
	}

	.grid-line {
		stroke: rgba(255, 244, 225, 0.06);
		stroke-width: 1;
	}

	.axis-text {
		fill: var(--text-muted);
		font-size: 10px;
	}

	.axis-text.y-axis {
		text-anchor: end;
	}

	.axis-sub {
		fill: var(--text-faint);
		font-size: 9px;
	}

	.limit-line {
		stroke-width: 1;
		stroke-dasharray: 4 4;
	}

	.limit-line.pv-limit {
		stroke: rgba(232, 137, 12, 0.5);
	}

	.limit-line.load-limit {
		stroke: rgba(45, 132, 214, 0.45);
	}

	.limit-label {
		font-size: 9.5px;
		font-weight: 500;
		text-anchor: end;
		fill: currentColor;
	}

	.point-pv {
		fill: var(--color-pv);
	}

	.point-load {
		fill: var(--color-load);
	}

	.point-pv.active,
	.point-load.active {
		stroke: var(--surface);
		stroke-width: 2.2;
	}

	.cursor-guide {
		stroke: rgba(255, 244, 225, 0.28);
		stroke-width: 1;
		stroke-dasharray: 2 3;
	}

	.hit-column {
		cursor: crosshair;
	}

	@media (max-width: 760px) {
		.chart-header,
		.guide-panel,
		.telemetry-bar {
			padding-inline: 1.25rem;
		}

		.chart-title {
			font-size: 1.55rem;
		}
	}
</style>
