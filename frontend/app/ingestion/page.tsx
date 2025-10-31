'use client';

import { DashboardHeader } from '@/components/dashboard-header';
import { EntityUploadCard } from '@/components/entity-upload-card';
import { useOrganization } from '@/lib/organization-context';
import { Factory, Package, Truck, Users, ShoppingCart, Route } from 'lucide-react';

// Ingestion flow order
const ENTITY_TYPES = [
  {
    id: 'suppliers',
    name: 'Suppliers',
    description: 'Upload vendor and supplier master data',
    icon: Users,
    acceptedSystems: ['SAP'],
    sampleFields: 'LIFNR, NAME1, ORT01, LAND1, PSTLZ',
  },
  {
    id: 'products',
    name: 'Products',
    description: 'Upload product catalog and SKU information',
    icon: ShoppingCart,
    acceptedSystems: ['SAP'],
    sampleFields: 'MATNR, MAKTX, MEINS, NTGEW',
  },
  {
    id: 'facilities',
    name: 'Facilities',
    description: 'Upload factory, warehouse, and distribution center locations',
    icon: Factory,
    acceptedSystems: ['SAP', 'D365', 'Oracle'],
    sampleFields: 'WERKS, NAME1, ORT01, LAND1, LATITUDE, LONGITUDE',
  },
  {
    id: 'routes',
    name: 'Routes',
    description: 'Upload transport routes and shipping lanes',
    icon: Route,
    acceptedSystems: ['SAP'],
    sampleFields: 'ROUTE_ID, ORIGIN, DESTINATION, DISTANCE_KM',
  },
  {
    id: 'purchase_orders',
    name: 'Purchase Orders',
    description: 'Upload procurement and purchase order records',
    icon: Truck,
    acceptedSystems: ['SAP'],
    sampleFields: 'EBELN, LIFNR, BEDAT, MENGE',
  },
  {
    id: 'shipments',
    name: 'Shipments',
    description: 'Upload delivery and shipment transaction records',
    icon: Package,
    acceptedSystems: ['SAP', 'D365', 'Oracle'],
    sampleFields: 'VBELN, VSTEL, KUNNR, WADAT, BTGEW',
  },
];

export default function IngestionPage() {
  const { orgId } = useOrganization();

  if (!orgId) {
    return (
      <div>
        <DashboardHeader />
        <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-8">
          <div className="text-center">
            <p className="text-muted-foreground">Please select an organization to upload data.</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div>
      <DashboardHeader />
      <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-32 space-y-6 md:space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Ingestion</h1>
          <p className="text-muted-foreground mt-2">
            Upload CSV files from your ERP systems (SAP, D365, Oracle) to build your supply chain knowledge graph
          </p>
        </div>

        {/* Simple flow guide */}
        <section className="rounded-xl border bg-card p-4 shadow-sm">
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Recommended upload & import order</h2>
          <div className="flex flex-wrap items-center gap-2">
            {ENTITY_TYPES.map((s, i) => (
              <div key={s.id} className="flex items-center gap-2">
                <div className="rounded-lg border px-3 py-1.5 text-sm bg-background">{s.name}</div>
                {i < ENTITY_TYPES.length - 1 && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <div className="h-px w-6 bg-border" />
                    <svg viewBox="0 0 20 20" width="18" height="18" fill="currentColor" className="opacity-70">
                      <path d="M7 5l5 5-5 5" />
                    </svg>
                    <div className="h-px w-6 bg-border" />
                  </div>
                )}
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Tip: EO backfill/enrichment can be run after Facilities are imported.</p>
        </section>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {ENTITY_TYPES.map((entity) => (
            <EntityUploadCard
              key={entity.id}
              entityType={entity.id}
              name={entity.name}
              description={entity.description}
              icon={entity.icon}
              acceptedSystems={entity.acceptedSystems}
              sampleFields={entity.sampleFields}
              orgId={orgId}
            />
          ))}
        </div>
      </main>
    </div>
  );
}
