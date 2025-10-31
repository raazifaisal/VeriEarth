"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { useState } from "react";

interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  requireConfirmation?: boolean;
  confirmationText?: string;
  entityName?: string;
}

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "Delete",
  cancelText = "Cancel",
  onConfirm,
  requireConfirmation = false,
  confirmationText,
  entityName,
}: ConfirmationDialogProps) {
  const [inputValue, setInputValue] = useState("");

  const handleConfirm = () => {
    if (requireConfirmation && inputValue !== confirmationText) {
      return;
    }
    onConfirm();
    setInputValue("");
    onOpenChange(false);
  };

  const isConfirmDisabled = requireConfirmation && inputValue !== confirmationText;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="text-red-600">{title}</AlertDialogTitle>
          <AlertDialogDescription className="text-sm text-muted-foreground">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        
        {requireConfirmation && (
          <div className="py-4">
            <p className="text-sm font-medium mb-2">
              To confirm, type <span className="font-mono bg-muted px-1 rounded">{confirmationText}</span> in the box below:
            </p>
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={confirmationText}
              className="font-mono"
            />
          </div>
        )}
        
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => setInputValue("")}>
            {cancelText}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isConfirmDisabled}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            {confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
