/**
 * Student Drilldown - Rendering Functions Part 2
 * Additional rendering functions for tables, charts, and data display
 */

// ============================================================================
// TABLE & LIST RENDERING
// ============================================================================

function iconForDepthType(t) {
    if (t === 'Stuck') return '<span class="text-amber-500" title="Stuck">⚠</span>';
    if (t === 'Skimming') return '<span class="text-sky-500" title="Skimming">ⓘ</span>';
    if (t === 'Deep Dive') return '<span class="text-emerald-500" title="Deep Dive">✓</span>';
    return '';
}

function renderDepthRows(rows) {
    const tbody = document.getElementById('depth-table-body');
    const empty = document.getElementById('depth-empty');
    tbody.innerHTML = '';
    const f = document.getElementById('depth-filter').value;
    const filtered = f ? rows.filter(r => r.engagement_type === f) : rows;
    if (!filtered.length) {
        empty.classList.remove('hidden');
        return;
    }
    empty.classList.add('hidden');
    filtered.forEach(r => {
        const tr = document.createElement('tr');
        let rowClass = '';
        if (r.engagement_type === 'Stuck') rowClass = 'bg-amber-50/80';
        tr.className = rowClass;
        tr.innerHTML = `
            <td class="py-2 pr-4 font-medium text-slate-800">${iconForDepthType(r.engagement_type)} ${escapeHtml(r.resource_name || '')}</td>
            <td class="py-2 pr-4">${escapeHtml(r.engagement_type || '')}</td>
            <td class="py-2 pr-4 font-mono">${r.depth_ratio != null ? Number(r.depth_ratio).toFixed(2) : '—'}</td>`;
        tbody.appendChild(tr);
    });
}

function renderDeadlinesSection(deadlines) {
    const wrap = document.getElementById('deadlines-list');
    wrap.innerHTML = '';
    if (!deadlines || !deadlines.length) {
        document.getElementById('deadlines-section').classList.add('hidden');
        return;
    }
    document.getElementById('deadlines-section').classList.remove('hidden');
    deadlines.forEach(d => {
        const p = (d.pressure_level || '').toString();
        let bg = 'bg-emerald-50 border-emerald-100';
        if (p.toLowerCase() === 'critical') bg = 'bg-red-50 border-red-200';
        else if (p.toLowerCase() === 'warning') bg = 'bg-amber-50 border-amber-200';
        const div = document.createElement('div');
        div.className = `p-4 rounded-xl border ${bg}`;
        const hrs = d.hours_before_deadline != null ? Number(d.hours_before_deadline).toFixed(1) : '—';
        div.innerHTML = `<div class="font-bold text-slate-900">${escapeHtml(d.resource_name || '')}</div>
            <div class="text-xs text-slate-600 mt-1">Deadline: ${escapeHtml(String(d.deadline_date || ''))} · ${hrs}h left · <strong>${escapeHtml(p)}</strong></div>`;
        wrap.appendChild(div);
    });
}

function renderComparisonSection(cmp) {
    if (!cmp) return;
    document.getElementById('comparison-section').classList.remove('hidden');
    document.getElementById('cmp-eng').textContent =
        `${cmp.student_avg_engagement} vs ${cmp.class_avg_engagement} (${formatDiffPct(cmp.engagement_diff_pct)})`;
    document.getElementById('cmp-risk').textContent =
        `${cmp.student_avg_risk} vs ${cmp.class_avg_risk} (${formatDiffPct(cmp.risk_diff_pct)})`;
    document.getElementById('cmp-prog').textContent =
        `${cmp.student_progress_pct}% vs ${cmp.class_avg_progress}% (${formatDiffPct(cmp.progress_diff_pct)})`;
    const pr = cmp.percentile_rank;
    const pctLabel = pr >= 50 ? `Top ${100 - pr}%` : `Bottom ${pr}%`;
    document.getElementById('cmp-pct').textContent = pctLabel;
    document.getElementById('below-avg-banner').classList.toggle('hidden', !cmp.below_avg_engagement);
}

// ============================================================================
// SANKEY DIAGRAM
// ============================================================================

function renderSankeyStudent(linksRaw) {
    const container = document.getElementById('student-sankey');
    const backList = document.getElementById('back-edges-list');
    container.innerHTML = '';
    backList.innerHTML = '';
    backList.classList.add('hidden');
    document.getElementById('back-edge-note').classList.add('hidden');

    if (!linksRaw || !linksRaw.length) {
        document.getElementById('transitions-section').classList.add('hidden');
        return;
    }
    document.getElementById('transitions-section').classList.remove('hidden');

    const forward = [];
    const backward = [];
    const toCount = {};
    linksRaw.forEach(d => {
        const c = parseInt(d.transition_count, 10) || 0;
        const tk = String(d.to_key);
        toCount[tk] = (toCount[tk] || 0) + c;
        const cmp = String(d.from_key).localeCompare(String(d.to_key));
        const row = {
            from_res: d.from_resource,
            to_res: d.to_resource,
            transition_count: d.transition_count,
            from_key: d.from_key,
            to_key: d.to_key
        };
        if (cmp > 0) backward.push(row);
        else forward.push(row);
    });

    let loopDetected = false;
    Object.keys(toCount).forEach(k => {
        if (toCount[k] > 3) loopDetected = true;
    });
    document.getElementById('review-loop-banner').classList.toggle('hidden', !loopDetected);

    if (backward.length) {
        document.getElementById('back-edge-note').classList.remove('hidden');
        backList.classList.remove('hidden');
        backward.forEach(b => {
            const li = document.createElement('li');
            li.className = 'p-2 rounded-lg bg-orange-50 border border-orange-200 text-orange-900';
            li.textContent = `${b.from_res} → ${b.to_res} (${b.transition_count})`;
            backList.appendChild(li);
        });
    }

    const mapped = forward.map(d => ({
        from_res: d.from_res,
        to_res: d.to_res,
        transition_count: d.transition_count
    }));

    const height = 360;
    const width = container.offsetWidth || 800;
    const svg = d3.select(container).append('svg')
        .attr('width', '100%').attr('height', height)
        .attr('viewBox', `0 0 ${width} ${height}`);

    const sankey = d3.sankey()
        .nodeWidth(15)
        .nodePadding(12)
        .extent([[1, 1], [width - 1, height - 6]]);

    const nodes = Array.from(new Set([...mapped.map(d => d.from_res), ...mapped.map(d => d.to_res)]))
        .map(name => ({ name }));
    const nodeMap = new Map(nodes.map((d, i) => [d.name, i]));
    const processedLinks = [];
    mapped.forEach(d => {
        const s = nodeMap.get(d.from_res);
        const t = nodeMap.get(d.to_res);
        if (s !== undefined && t !== undefined && s < t) {
            processedLinks.push({ source: s, target: t, value: Math.max(1, parseInt(d.transition_count, 10)) });
        }
    });

    if (processedLinks.length === 0) {
        container.innerHTML = '<p class="text-slate-400 text-sm italic py-8 text-center">Not enough linear flow data for Sankey.</p>';
        return;
    }

    const graph = sankey({
        nodes: nodes.map(d => Object.assign({}, d)),
        links: processedLinks.map(d => Object.assign({}, d))
    });

    const color = d3.scaleOrdinal(d3.schemeCategory10);
    svg.append('g')
        .attr('fill', 'none')
        .attr('stroke-opacity', 0.35)
        .selectAll('path')
        .data(graph.links)
        .join('path')
        .attr('d', d3.sankeyLinkHorizontal())
        .attr('stroke', d => color(d.source.name))
        .attr('stroke-width', d => Math.max(1, d.width))
        .append('title')
        .text(d => `${d.source.name} → ${d.target.name}\n${d.value}`);

    const node = svg.append('g')
        .selectAll('g')
        .data(graph.nodes)
        .join('g');

    node.append('rect')
        .attr('x', d => d.x0)
        .attr('y', d => d.y0)
        .attr('height', d => d.y1 - d.y0)
        .attr('width', d => d.x1 - d.x0)
        .attr('fill', d => color(d.name))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1);

    node.append('text')
        .attr('x', d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
        .attr('y', d => (d.y1 + d.y0) / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .attr('fill', '#475569')
        .text(d => d.name.length > 28 ? d.name.substring(0, 25) + '...' : d.name);
}

// ============================================================================
// LIFECYCLE & HEATMAP
// ============================================================================

function estimateCompletionDate(ms, currentPct) {
    const pts = [];
    if (ms.milestone_25_date) pts.push({ p: 25, d: new Date(ms.milestone_25_date) });
    if (ms.milestone_50_date) pts.push({ p: 50, d: new Date(ms.milestone_50_date) });
    if (ms.milestone_75_date) pts.push({ p: 75, d: new Date(ms.milestone_75_date) });
    if (pts.length < 2) return null;
    pts.sort((a, b) => a.d - b.d);
    let sum = 0;
    let n = 0;
    for (let i = 1; i < pts.length; i++) {
        const dp = pts[i].p - pts[i - 1].p;
        const dd = (pts[i].d - pts[i - 1].d) / 86400000;
        if (dp > 0 && dd >= 0) {
            sum += dd / (dp / 25);
            n++;
        }
    }
    if (!n) return null;
    const daysPer25 = sum / n;
    const remaining = 100 - (currentPct || 0);
    if (remaining <= 0) return null;
    const est = new Date();
    est.setDate(est.getDate() + (remaining / 25) * daysPer25);
    return est;
}

function renderLifecycleSection(ms, overview) {
    const sec = document.getElementById('lifecycle-section');
    const grid = document.getElementById('milestone-grid');
    const drop = document.getElementById('dropout-banner');
    const estEl = document.getElementById('est-completion');
    grid.innerHTML = '';
    estEl.textContent = '';
    drop.classList.add('hidden');

    if (!ms || Object.keys(ms).length === 0) {
        sec.classList.add('hidden');
        return;
    }
    sec.classList.remove('hidden');

    const fmt = (v) => {
        if (!v) return 'Not reached';
        try {
            return new Date(v).toLocaleDateString();
        } catch (e) {
            return String(v);
        }
    };

    [
        { label: '25%', v: ms.milestone_25_date },
        { label: '50%', v: ms.milestone_50_date },
        { label: '75%', v: ms.milestone_75_date },
        { label: '100%', v: ms.completion_date }
    ].forEach(m => {
        const box = document.createElement('div');
        box.className = 'p-3 rounded-xl bg-slate-50 border border-slate-100';
        box.innerHTML = `<div class="text-xs text-slate-500">${m.label}</div>
            <div class="font-semibold text-slate-900">${fmt(m.v)}</div>`;
        grid.appendChild(box);
    });

    if (overview && overview.current_status === 'Dropout' && ms.dropout_date) {
        drop.classList.remove('hidden');
        drop.textContent = `Dropout recorded on ${fmt(ms.dropout_date)}. Student may need re-engagement.`;
    }

    const est = estimateCompletionDate(ms, overview ? overview.current_progress_pct : 0);
    if (est) {
        estEl.textContent = `Estimated completion: ${est.toLocaleDateString()}`;
    }
}

function renderHeatmapSection(daily) {
    const section = document.getElementById('heatmap-section');
    const container = document.getElementById('daily-heatmap');
    container.innerHTML = '';
    if (!daily || !daily.length) {
        section.classList.add('hidden');
        return;
    }
    section.classList.remove('hidden');

    const sorted = [...daily].sort((a, b) => {
        const da = new Date(a.year, (parseInt(a.month, 10) || 1) - 1, parseInt(a.date, 10) || 1);
        const db = new Date(b.year, (parseInt(b.month, 10) || 1) - 1, parseInt(b.date, 10) || 1);
        return da - db;
    });

    let streak = 0;
    let streakStart = 0;
    const inStreak = new Set();
    const flushStreak = (endIdx) => {
        if (streak > 3) {
            for (let j = streakStart; j < endIdx; j++) inStreak.add(j);
        }
    };
    sorted.forEach((d, i) => {
        const score = parseInt(d.engagement_score, 10) || 0;
        if (score === 0) {
            if (streak === 0) streakStart = i;
            streak++;
        } else {
            flushStreak(i);
            streak = 0;
        }
    });
    flushStreak(sorted.length);

    sorted.forEach((d, i) => {
        const score = parseInt(d.engagement_score, 10) || 0;
        const el = document.createElement('div');
        el.className = 'w-5 h-5 sm:w-6 sm:h-6 rounded-sm shrink-0';
        const label = `${d.date}/${d.month}/${d.year} · ${d.day_of_week || ''}`;
        el.title = `${label} | Engagement: ${score} | Resource: ${d.total_resource_access} | Quiz: ${d.total_quiz_attempt}`;
        if (score === 0) el.style.background = '#cbd5e1';
        else {
            const t = Math.min(1, score / 100);
            el.style.background = `rgb(${30 + Math.round(80 * t)}, ${64 + Math.round(60 * t)}, ${175 + Math.round(40 * t)})`;
        }
        if (inStreak.has(i)) el.style.boxShadow = '0 0 0 2px #ef4444';
        container.appendChild(el);
    });
}

// ============================================================================
// INSIGHTS
// ============================================================================

function hasCrammingSpike(weekly) {
    if (!weekly || weekly.length < 2) return false;
    const scores = weekly.map(w => parseInt(w.engagement_score, 10) || 0);
    for (let i = 1; i < scores.length; i++) {
        const prev = scores[i - 1];
        if (prev > 0 && ((scores[i] - prev) / prev) > 3) return true;
    }
    return false;
}

function buildInsights(data) {
    const o = data.overview || {};
    const cmp = data.comparison || {};
    const items = [];

    if (o.risk_level === 'High') {
        items.push({ priority: 1, category: 'Risk', text: 'Schedule 1-on-1 meeting with student.' });
    }
    if ((o.days_since_last_activity || 0) > 7) {
        items.push({ priority: 1, category: 'Engagement', text: 'Send reminder email to re-engage.' });
    }
    const stuck = (data.engagement_depth || []).filter(r => r.engagement_type === 'Stuck');
    if (stuck.length > 2) {
        const names = stuck.slice(0, 6).map(r => r.resource_name).filter(Boolean).join(', ');
        items.push({ priority: 2, category: 'Progress', text: `Provide additional support for: ${names}` });
    }
    if (hasCrammingSpike(data.engagement_trend)) {
        items.push({ priority: 2, category: 'Engagement', text: 'Encourage consistent study habits (cramming detected).' });
    }
    if (cmp.below_avg_engagement) {
        items.push({ priority: 2, category: 'Engagement', text: 'Consider peer mentoring or study group.' });
    }
    if ((data.critical_deadline_count || 0) > 2) {
        items.push({ priority: 1, category: 'Deadline', text: 'Multiple critical deadlines — consider extension.' });
    }

    items.sort((a, b) => a.priority - b.priority);
    return items;
}

function renderInsightsSection(data) {
    const list = document.getElementById('insights-list');
    const sec = document.getElementById('insights-section');
    list.innerHTML = '';
    const insights = buildInsights(data);
    if (!insights.length) {
        sec.classList.add('hidden');
        return;
    }
    sec.classList.remove('hidden');
    insights.forEach(ins => {
        const badge = ins.priority === 1 ? 'bg-red-100 text-red-800' : 'bg-amber-50 text-amber-900';
        const pr = ins.priority === 1 ? 'High' : 'Medium';
        const row = document.createElement('div');
        row.className = 'p-4 rounded-xl border border-slate-100 bg-white flex gap-3';
        row.innerHTML = `
            <span class="text-xs font-bold px-2 py-1 rounded ${badge}">${pr}</span>
            <div>
                <div class="text-xs uppercase text-slate-400 font-bold mb-1">${escapeHtml(ins.category)}</div>
                <div class="text-sm text-slate-800">${escapeHtml(ins.text)}</div>
            </div>`;
        list.appendChild(row);
    });
}

function setSectionVisibility(data) {
    const hasDepth = data.engagement_depth && data.engagement_depth.length;
    document.getElementById('depth-section').classList.toggle('hidden', !hasDepth);
}
