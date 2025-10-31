'use client';

import { useOrganization } from '@/lib/organization-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Building2, Plus, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

export function OrgSelector() {
  const { orgId, setOrgId } = useOrganization();
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [orgName, setOrgName] = useState('');
  const queryClient = useQueryClient();

  const { data: organizations, isLoading } = useQuery({
    queryKey: ['organizations'],
    queryFn: () => dashboardApi.getOrganizations(),
  });

  const createOrgMutation = useMutation({
    mutationFn: (name: string) => dashboardApi.createOrganization(name),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      setOrgId(data.id);
      setShowAddDialog(false);
      setOrgName('');
      toast.success('Organization created successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create organization');
    },
  });

  const handleAddOrganization = () => {
    setShowAddDialog(true);
  };

  const handleCreateOrganization = (e: React.FormEvent) => {
    e.preventDefault();
    if (orgName.trim()) {
      createOrgMutation.mutate(orgName.trim());
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-muted-foreground" />
        <div className="w-[200px] h-10 bg-muted animate-pulse rounded-md" />
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-muted-foreground" />
        <Select value={orgId || undefined} onValueChange={setOrgId}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Select organization" />
          </SelectTrigger>
          <SelectContent>
            {organizations && organizations.length > 0 ? (
              <>
                {organizations.map((org: any) => (
                  <SelectItem key={org.id} value={org.id}>
                    {org.name}
                  </SelectItem>
                ))}
                <div className="border-t mt-1 pt-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start"
                    onClick={handleAddOrganization}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add New Organization
                  </Button>
                </div>
              </>
            ) : (
              <div className="p-2">
                <p className="text-sm text-muted-foreground mb-2">No organizations found</p>
                <Button
                  size="sm"
                  className="w-full"
                  onClick={handleAddOrganization}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Organization
                </Button>
              </div>
            )}
          </SelectContent>
        </Select>
      </div>

      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <form onSubmit={handleCreateOrganization}>
            <DialogHeader>
              <DialogTitle>Create New Organization</DialogTitle>
              <DialogDescription>
                Add a new organization to manage your supply chain data.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Organization Name</Label>
                <Input
                  id="name"
                  placeholder="Acme Corporation"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                  autoFocus
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowAddDialog(false)}
                disabled={createOrgMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createOrgMutation.isPending || !orgName.trim()}>
                {createOrgMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Create Organization
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
