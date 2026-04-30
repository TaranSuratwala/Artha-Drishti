import React, { useState, useRef, useCallback, useMemo } from 'react';

/**
 * Interactive SVG Price Chart with hover crosshair, tooltip, OHLC data, and volume bars.
 */
export const PriceChart = ({ data, height = 340, showVolume = true }) => {
    const [hover, setHover] = useState(null);
    const svgRef = useRef(null);
    const points = useMemo(() => (Array.isArray(data) ? data : []), [data]);

    const width = 750;
    const padding = { top: 20, right: 62, bottom: showVolume ? 80 : 45, left: 65 };
    const chartWidth = width - padding.left - padding.right;
    const volHeight = showVolume ? 42 : 0;
    const chartHeight = height - padding.top - padding.bottom - (showVolume ? volHeight + 12 : 0);

    const { prices, minPrice, priceRange, maxVol } = useMemo(() => {
        if (!points.length) return { prices: [], minPrice: 0, priceRange: 1, maxVol: 1 };
        const p = points.map(d => d.close || d.value || 0);
        const v = points.map(d => d.volume || 0);
        const mn = Math.min(...p);
        const mx = Math.max(...p);
        return { prices: p, minPrice: mn, priceRange: mx - mn || 1, maxVol: Math.max(...v) || 1 };
    }, [points]);

    const dataLength = points.length;

    const scaleX = (i) => (i / Math.max(1, dataLength - 1)) * chartWidth;
    const scaleY = (p) => chartHeight - ((p - minPrice) / priceRange) * chartHeight;
    const scaleVol = (v) => (v / maxVol) * volHeight;

    const handleMouseLeave = useCallback(() => setHover(null), []);
    const isUp = prices[prices.length - 1] >= prices[0];
    const lineColor = isUp ? '#22c55e' : '#ef4444';
    const fillId = isUp ? 'areaGUp' : 'areaGDn';

    const linePath = points.map((_, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(prices[i])}`).join(' ');
    const areaPath = `${linePath} L ${chartWidth} ${chartHeight} L 0 ${chartHeight} Z`;

    const yTicks = Array.from({ length: 5 }, (_, i) => minPrice + (priceRange / 4) * i);
    const xStep = Math.max(1, Math.floor(dataLength / 8));
    const xIndices = Array.from({ length: Math.min(8, dataLength) }, (_, i) => i * xStep).filter(i => i < dataLength);

    const handleMouseMove = useCallback((e) => {
        const svg = svgRef.current;
        if (!svg) return;
        const rect = svg.getBoundingClientRect();
        const svgW = rect.width;
        const mx = ((e.clientX - rect.left) / svgW) * width - padding.left;
        if (mx < 0 || mx > chartWidth) { setHover(null); return; }
        const idx = Math.round((mx / chartWidth) * (dataLength - 1));
        const ci = Math.max(0, Math.min(dataLength - 1, idx));
        const x = (ci / Math.max(1, dataLength - 1)) * chartWidth;
        const y = chartHeight - ((prices[ci] - minPrice) / priceRange) * chartHeight;
        setHover({ idx: ci, x, y });
    }, [chartHeight, chartWidth, dataLength, minPrice, padding.left, priceRange, prices, width]);

    if (!dataLength) return null;

    const fmtDate = (d) => {
        if (!d?.date) return '';
        return new Date(d.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' });
    };
    const fmtPrice = (p) => `₹${Number(p).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const fmtVol = (v) => {
        if (v >= 1e7) return `${(v / 1e7).toFixed(1)}Cr`;
        if (v >= 1e5) return `${(v / 1e5).toFixed(1)}L`;
        if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
        return v?.toString() || '0';
    };

    const hd = hover ? points[hover.idx] : null;

    return (
        <div className="w-full relative select-none">
            {/* OHLCV info bar */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-2 min-h-[24px] px-1">
                {hd ? (
                    <>
                        <span className="text-xs text-gray-400 font-medium">{fmtDate(hd)}</span>
                        <span className="text-xs text-gray-400">O: <span className="text-white font-semibold">{fmtPrice(hd.open)}</span></span>
                        <span className="text-xs text-gray-400">H: <span className="text-green-400 font-semibold">{fmtPrice(hd.high)}</span></span>
                        <span className="text-xs text-gray-400">L: <span className="text-red-400 font-semibold">{fmtPrice(hd.low)}</span></span>
                        <span className="text-xs text-gray-400">C: <span className="text-white font-bold">{fmtPrice(hd.close || hd.value)}</span></span>
                        {hd.volume > 0 && <span className="text-xs text-gray-400">Vol: <span className="text-blue-300 font-semibold">{fmtVol(hd.volume)}</span></span>}
                    </>
                ) : (
                    <span className="text-xs text-gray-500 italic">Hover over chart to see OHLCV details</span>
                )}
            </div>

            <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="xMidYMid meet"
                onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}
                style={{ cursor: hover ? 'crosshair' : 'default' }}>
                <defs>
                    <linearGradient id="areaGUp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity="0.35" />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity="0.02" />
                    </linearGradient>
                    <linearGradient id="areaGDn" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity="0.35" />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity="0.02" />
                    </linearGradient>
                </defs>

                <g transform={`translate(${padding.left}, ${padding.top})`}>
                    {/* Y-axis grid + labels */}
                    {yTicks.map((tick, i) => (
                        <g key={`y-${i}`}>
                            <line x1={0} y1={scaleY(tick)} x2={chartWidth} y2={scaleY(tick)} stroke="#374151" strokeDasharray="4 4" opacity="0.3" />
                            <text x={-10} y={scaleY(tick)} textAnchor="end" dominantBaseline="middle" fill="#9ca3af" fontSize="11">₹{tick.toFixed(0)}</text>
                        </g>
                    ))}

                    {/* Area + line */}
                    <path d={areaPath} fill={`url(#${fillId})`} />
                    <path d={linePath} fill="none" stroke={lineColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

                    {/* Volume bars */}
                    {showVolume && (
                        <g transform={`translate(0, ${chartHeight + 12})`}>
                            {points.map((d, i) => {
                                const bw = Math.max(1, chartWidth / dataLength - 0.5);
                                const bh = scaleVol(d.volume || 0);
                                const up = (d.close || 0) >= (d.open || 0);
                                return <rect key={i} x={scaleX(i) - bw / 2} y={volHeight - bh} width={bw} height={bh} fill={up ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)'} rx="1" />;
                            })}
                        </g>
                    )}

                    {/* X-axis labels */}
                    {xIndices.map(idx => {
                        const d = points[idx];
                        if (!d) return null;
                        const label = new Date(d.date).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });
                        return <text key={`x-${idx}`} x={scaleX(idx)} y={chartHeight + (showVolume ? volHeight + 24 : 22)} textAnchor="middle" fill="#9ca3af" fontSize="10">{label}</text>;
                    })}

                    {/* Hover crosshair + dot + price tag */}
                    {hover && (
                        <>
                            <line x1={hover.x} y1={0} x2={hover.x} y2={chartHeight + (showVolume ? volHeight + 12 : 0)} stroke="#94a3b8" strokeDasharray="3 3" strokeWidth="1" opacity="0.6" />
                            <line x1={0} y1={hover.y} x2={chartWidth} y2={hover.y} stroke="#94a3b8" strokeDasharray="3 3" strokeWidth="1" opacity="0.6" />
                            <circle cx={hover.x} cy={hover.y} r="5" fill={lineColor} stroke="#fff" strokeWidth="2" />
                            <rect x={chartWidth + 4} y={hover.y - 10} width="54" height="20" rx="4" fill="#334155" />
                            <text x={chartWidth + 8} y={hover.y + 4} fill="#fff" fontSize="10" fontWeight="bold">₹{prices[hover.idx].toFixed(0)}</text>
                        </>
                    )}

                    {/* Latest price label */}
                    {prices.length > 1 && (
                        <text x={chartWidth + 8} y={scaleY(prices[prices.length - 1]) + 4} fill={lineColor} fontSize="10" fontWeight="bold">
                            ₹{prices[prices.length - 1].toFixed(2)}
                        </text>
                    )}
                </g>
            </svg>
        </div>
    );
};

export default PriceChart;
