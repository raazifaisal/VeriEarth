'use client';

import { useState } from 'react';
import { useOrganization } from '@/lib/organization-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DashboardHeader } from '@/components/dashboard-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table';
import { ConfirmationDialog } from '@/components/confirmation-dialog';
import { 
  Factory, 
  Users, 
  Package, 
  ShoppingCart, 
  Truck, 
  Route as RouteIcon,
  Trash2,
  RefreshCw,
  Database
} from 'lucide-react';
import { toast } from 'sonner';
import { dataManagementApi } from '@/lib/api';

const ENTITY_TYPES = [
  { id: 'facilities', name: 'Facilities', icon: Factory, color: 'text-blue-600' },
  { id: 'suppliers', name: 'Suppliers', icon: Users, color: 'text-purple-600' },
  { id: 'products', name: 'Products', icon: Package, color: 'text-green-600' },
  { id: 'purchase_orders', name: 'Purchase Orders', icon: ShoppingCart, color: 'text-orange-600' },
  { id: 'shipments', name: 'Shipments', icon: Truck, color: 'text-red-600' },
  { id: 'routes', name: 'Routes', icon: RouteIcon, color: 'text-teal-600' },
];

export default function DataManagementPage() {
  const { orgId } = useOrganization();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('facilities');
  const [masterClearOpen, setMasterClearOpen] = useState(false);
  const [masterPassword, setMasterPassword] = useState('');
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    type: 'delete' | 'clearAll' | null;
    title: string;
    description: string;
    entityName?: string;
  }>({
    open: false,
    type: null,
    title: '',
    description: '',
  });

  const { data: entityData = [], isLoading } = useQuery({
    queryKey: ['entity-data', activeTab, orgId],
    queryFn: () => dataManagementApi.getEntityData(activeTab, orgId as string),
    enabled: !!orgId,
  });

  const { data: stats } = useQuery({
    queryKey: ['entity-stats', orgId],
    queryFn: () => dataManagementApi.getStats(orgId as string),
    enabled: !!orgId,
  });

  const deleteMutation = useMutation({
    mutationFn: ({ entityType, id }: { entityType: string; id: string }) =>
      dataManagementApi.deleteEntity(entityType, id, orgId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-data', activeTab, orgId] });
      queryClient.invalidateQueries({ queryKey: ['entity-stats', orgId] });
      toast.success('Record deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete record');
    },
  });

  const clearAllMutation = useMutation({
    mutationFn: (entityType: string) =>
      dataManagementApi.clearAll(entityType, orgId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-data', activeTab, orgId] });
      queryClient.invalidateQueries({ queryKey: ['entity-stats', orgId] });
      toast.success('All records cleared successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to clear records');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ entityType, id, data }: { entityType: string; id: string; data: any }) =>
      dataManagementApi.updateEntity(entityType, id, data, orgId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-data', activeTab, orgId] });
      toast.success('Record updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update record');
    },
  });

  const masterClearMutation = useMutation({
    mutationFn: (password: string) => dataManagementApi.clearOrganization(orgId as string, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-data'] });
      queryClient.invalidateQueries({ queryKey: ['entity-stats'] });
      toast.success('Organization data cleared');
      setMasterPassword('');
      setMasterClearOpen(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to clear organization');
    }
  });

  const handleDelete = (id: string) => {
    const entityName = ENTITY_TYPES.find(e => e.id === activeTab)?.name || activeTab;
    setConfirmDialog({
      open: true,
      type: 'delete',
      title: `Delete ${entityName} Record`,
      description: `Are you sure you want to delete this ${entityName.toLowerCase()} record? This action cannot be undone.`,
      entityName: id,
    });
  };

  const handleClearAll = () => {
    const entityName = ENTITY_TYPES.find(e => e.id === activeTab)?.name || activeTab;
    setConfirmDialog({
      open: true,
      type: 'clearAll',
      title: `Delete All ${entityName}`,
      description: `This will permanently delete ALL ${entityName.toLowerCase()} records. This action cannot be undone.`,
      entityName: activeTab,
    });
  };

  const handleConfirmAction = () => {
    if (confirmDialog.type === 'delete' && confirmDialog.entityName) {
      deleteMutation.mutate({ entityType: activeTab, id: confirmDialog.entityName });
    } else if (confirmDialog.type === 'clearAll') {
      clearAllMutation.mutate(activeTab);
    }
  };

  const handleUpdate = (id: string, data: any) => {
    updateMutation.mutate({ entityType: activeTab, id, data });
  };

  if (!orgId) {
    return (
      <div>
        <DashboardHeader />
        <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-8">
          <div className="text-center">
            <p className="text-muted-foreground">
              Please select an organization to manage data.
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div>
      <DashboardHeader />
      <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-32 space-y-6 md:space-y-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Data Management</h1>
            <p className="text-muted-foreground mt-2">
              View, edit, and manage all imported supply chain data
            </p>
          </div>
          <div className="mt-1">
            <Button variant="destructive" size="sm" onClick={() => setMasterClearOpen(true)}>
              <Database className="mr-2 h-4 w-4" /> Master Clear Organization
            </Button>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          {ENTITY_TYPES.map((entity) => {
            const Icon = entity.icon;
            const count = stats?.[entity.id] || 0;
            return (
              <Card key={entity.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <Icon className={`h-5 w-5 ${entity.color}`} />
                    <Badge variant="secondary">{count}</Badge>
                  </div>
                  <CardTitle className="text-sm font-medium">{entity.name}</CardTitle>
                </CardHeader>
              </Card>
            );
          })}
        </div>

        {/* Data Tables */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Entity Data</CardTitle>
                <CardDescription>
                  Browse and manage imported records
                </CardDescription>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleClearAll}
                disabled={clearAllMutation.isPending || entityData.length === 0}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Clear All {activeTab}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3 lg:grid-cols-6">
                {ENTITY_TYPES.map((entity) => {
                  const Icon = entity.icon;
                  return (
                    <TabsTrigger key={entity.id} value={entity.id} className="text-xs">
                      <Icon className="h-4 w-4 mr-1" />
                      {entity.name}
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              {ENTITY_TYPES.map((entity) => (
                <TabsContent key={entity.id} value={entity.id} className="mt-6">
                  <DataTable
                    data={entityData}
                    entityType={entity.id}
                    isLoading={isLoading}
                    onDelete={handleDelete}
                    onUpdate={handleUpdate}
                  />
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </main>
      
      <ConfirmationDialog
        open={confirmDialog.open}
        onOpenChange={(open) => setConfirmDialog(prev => ({ ...prev, open }))}
        title={confirmDialog.title}
        description={confirmDialog.description}
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={handleConfirmAction}
        requireConfirmation={confirmDialog.type === 'clearAll'}
        confirmationText={confirmDialog.entityName}
        entityName={confirmDialog.entityName}
      />

      {/* Master clear dialog */}
      <Dialog open={masterClearOpen} onOpenChange={setMasterClearOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Master Clear Organization</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This deletes all facilities, routes, shipments, purchase orders, products, suppliers, and EO data for this organization. Enter the organization sudo password to proceed.
          </p>
          <Input
            type="password"
            placeholder="Organization sudo password"
            value={masterPassword}
            onChange={(e) => setMasterPassword(e.target.value)}
          />
          <DialogFooter>
            <Button
              variant="destructive"
              onClick={() => masterClearMutation.mutate(masterPassword)}
              disabled={!masterPassword || masterClearMutation.isPending}
            >
              {masterClearMutation.isPending ? 'Clearing...' : 'Confirm Clear'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

