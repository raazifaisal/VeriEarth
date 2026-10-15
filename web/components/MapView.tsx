'use client';

import { useEffect, useRef } from 'react';
import type { Edge, SiteRow } from '@/lib/api';

type L = typeof import('leaflet');

// Sequential orange scale for P(site down): light (unlikely) -> deep (likely).
export function riskColor(p: number | null): string {
  if (p == null) return '#7FB8D4';
  if (p < 0.1) return '#F2D9C4';
  if (p < 0.3) return '#EFB48A';
  if (p < 0.5) return '#E8894F';
  if (p < 0.7) return '#D9622B';
  return '#A8401A';
}

export default function MapView({
  sites, edges, selected, onSelect,
}: {
  sites: SiteRow[];
  edges: Edge[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<import('leaflet').Map | null>(null);
  const layer = useRef<import('leaflet').LayerGroup | null>(null);
  const leaflet = useRef<L | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = (await import('leaflet')).default as unknown as L;
      if (cancelled || !host.current || map.current) return;
      leaflet.current = L;
      map.current = L.map(host.current, { zoomControl: false, attributionControl: true }).setView([13.5, 100.9], 9);
      L.control.zoom({ position: 'bottomright' }).addTo(map.current);
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors',
        maxZoom: 16,
      }).addTo(map.current);
      new ResizeObserver(() => map.current?.invalidateSize()).observe(host.current);
      layer.current = L.layerGroup().addTo(map.current);
      draw();
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sites, edges, selected]);

  function draw() {
    const L = leaflet.current;
    const m = map.current;
    const g = layer.current;
    if (!L || !m || !g) return;
    g.clearLayers();
    const byId = Object.fromEntries(sites.map((s) => [s.id, s]));
    const local = sites.filter((s) => !s.overseas);

    for (const e of edges) {
      const a = byId[e.from];
      const b = byId[e.to];
      if (!a || !b || a.overseas || b.overseas) continue;
      const style =
        e.kind === 'supplies'
          ? { color: '#10201F', weight: 1.5, opacity: 0.45 }
          : e.kind === 'alternate'
            ? { color: '#2F6F8F', weight: 1.5, opacity: 0.6, dashArray: '4 6' }
            : { color: '#5C6563', weight: 1, opacity: 0.35, dashArray: '1 5' };
      L.polyline([[a.lat, a.lon], [b.lat, b.lon]], style).addTo(g);
    }

    for (const s of local) {
      const isSel = s.id === selected;
      let marker: import('leaflet').Layer;
      if (s.kind === 'supplier') {
        const r = s.alternate ? 7 : 10;
        marker = L.circleMarker([s.lat, s.lon], {
          radius: isSel ? r + 4 : r,
          color: s.alternate ? '#2F6F8F' : '#10201F',
          weight: isSel ? 3 : s.alternate ? 2 : 1.2,
          fillColor: riskColor(s.p_down),
          fillOpacity: 0.95,
        });
      } else {
        const color = s.kind === 'own_plant' ? '#2F6F8F' : s.kind === 'customer' ? '#10201F' : '#5C6563';
        const size = s.kind === 'own_plant' ? 16 : 12;
        marker = L.marker([s.lat, s.lon], {
          icon: L.divIcon({
            className: '',
            html: `<div style="width:${size}px;height:${size}px;background:${color};border:2px solid #FBFAF6;border-radius:${s.kind === 'customer' ? '50%' : '3px'};box-shadow:0 1px 4px rgba(0,0,0,.3)"></div>`,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
          }),
        });
      }
      const p = s.p_down == null ? '' : ` · P(down) ${Math.round(s.p_down * 100)}%`;
      marker
        .bindTooltip(`<b>${s.name}</b><br/><span style="color:#5C6563">${s.estate}${p}</span>`, { className: 'veri-tip', direction: 'top' })
        .on('click', () => onSelect(s.id))
        .addTo(g);
    }

    if (local.length && !(m as unknown as { _fitted?: boolean })._fitted) {
      m.invalidateSize();
      m.fitBounds(L.latLngBounds(local.map((s) => [s.lat, s.lon] as [number, number])), { padding: [40, 40] });
      (m as unknown as { _fitted?: boolean })._fitted = true;
    }
  }

  return <div ref={host} className="h-full w-full rounded-xl" />;
}
