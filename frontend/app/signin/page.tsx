'use client';

import { login } from '@/lib/api-secure';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Leaf, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import Link from 'next/link';

export default function SignInPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      await login(email, password);
      await refreshUser();
      router.push('/dashboard');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-black relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          className="absolute top-20 left-20 w-96 h-96 bg-emerald-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 dark:bg-emerald-500 dark:opacity-15 dark:mix-blend-lighten"
          animate={{
            scale: [1, 1.2, 1],
            x: [0, 50, 0],
          }}
          transition={{ duration: 15, repeat: Infinity }}
        />
        <motion.div
          className="absolute bottom-20 right-20 w-96 h-96 bg-emerald-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 dark:bg-emerald-400 dark:opacity-15 dark:mix-blend-lighten"
          animate={{
            scale: [1, 1.3, 1],
            x: [0, -50, 0],
          }}
          transition={{ duration: 18, repeat: Infinity }}
        />
      </div>

      {/* Header */}
      <header className="relative z-50 p-6">
        <Link href="/" className="flex items-center gap-3 group">
          <Leaf className="h-8 w-8 text-emerald-600 dark:text-emerald-500 transition-transform group-hover:scale-110" />
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              VeriEarth
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Supply Chain Intelligence
            </p>
          </div>
        </Link>
      </header>

      {/* Main content */}
      <div className="flex-1 flex items-center justify-center px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md"
        >
          <Card className="backdrop-blur-sm bg-white/95 dark:bg-slate-900/95 shadow-2xl border border-slate-200 dark:border-emerald-500/30">
            <CardHeader className="text-center space-y-4">
              <motion.div
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 3, repeat: Infinity }}
                className="mx-auto"
              >
                <Sparkles className="h-10 w-10 text-emerald-500 dark:text-emerald-400" />
              </motion.div>
              <div>
                <CardTitle className="text-3xl font-bold bg-gradient-to-r from-emerald-600 to-green-600 dark:from-emerald-400 dark:to-green-400 bg-clip-text text-transparent">
                  Welcome Back
                </CardTitle>
                <CardDescription className="text-base mt-2">
                  Sign in to your VeriEarth account
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="email" className="flex items-center gap-2">
                    <span>Email Address</span>
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                    required
                    className="border-emerald-200 focus:border-emerald-500 dark:border-emerald-800"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                    <Link
                      href="/forgot-password"
                      className="text-sm text-emerald-600 dark:text-emerald-400 hover:underline"
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                    required
                    className="border-emerald-200 focus:border-emerald-500 dark:border-emerald-800"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white shadow-lg hover:shadow-xl transition-all disabled:opacity-50"
                  size="lg"
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <motion.div
                        className="w-2 h-2 bg-white rounded-full"
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 0.6, repeat: Infinity }}
                      />
                      <motion.div
                        className="w-2 h-2 bg-white rounded-full"
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                      />
                      <motion.div
                        className="w-2 h-2 bg-white rounded-full"
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                      />
                    </div>
                  ) : (
                    'Sign In'
                  )}
                </Button>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-emerald-200 dark:border-emerald-800" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white dark:bg-slate-900 px-2 text-muted-foreground">
                      Or
                    </span>
                  </div>
                </div>

                <p className="text-sm text-center text-slate-600 dark:text-slate-400">
                  Don't have an account?{' '}
                  <Link
                    href="/signup"
                    className="text-emerald-600 dark:text-emerald-400 hover:underline font-medium"
                  >
                    Sign up
                  </Link>
                </p>
              </form>
            </CardContent>
          </Card>

          <div className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
            <p>
              By signing in, you agree to our{' '}
              <Link href="/terms" className="text-emerald-600 dark:text-emerald-400 hover:underline">
                Terms of Service
              </Link>{' '}
              and{' '}
              <Link href="/privacy" className="text-emerald-600 dark:text-emerald-400 hover:underline">
                Privacy Policy
              </Link>
            </p>
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 py-6 border-t border-emerald-200 dark:border-emerald-800 bg-white/50 dark:bg-slate-900/50">
        <div className="container mx-auto px-4 text-center text-sm text-slate-600 dark:text-slate-400">
          <p>© 2025 VeriEarth. Empower your supply chain decarbonization journey.</p>
        </div>
      </footer>
    </div>
  );
}

