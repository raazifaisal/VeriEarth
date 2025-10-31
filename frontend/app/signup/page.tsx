'use client';

import { register } from '@/lib/api-secure';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Leaf, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import Link from 'next/link';

export default function SignUpPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match');
      return;
    }
    
    setIsLoading(true);
    try {
      await register(formData.fullName, formData.email, formData.password);
      alert('Registration successful! Please check your email to verify your account.');
      router.push('/signin');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
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
      <div className="flex-1 flex items-center justify-center px-4 py-8 relative z-10">
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
                  Get Started
                </CardTitle>
                <CardDescription className="text-base mt-2">
                  Create your VeriEarth account to begin optimizing supply chain emissions
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="fullName">Full Name</Label>
                  <Input
                    id="fullName"
                    name="fullName"
                    type="text"
                    placeholder="John Doe"
                    value={formData.fullName}
                    onChange={handleChange}
                    required
                    className="border-emerald-200 focus:border-emerald-500 dark:border-emerald-800"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Business Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="you@company.com"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="border-emerald-200 focus:border-emerald-500 dark:border-emerald-800"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Create a secure password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    className="border-emerald-200 focus:border-emerald-500 dark:border-emerald-800"
                  />
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Must be at least 8 characters
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm Password</Label>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    placeholder="Re-enter your password"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    required
                    className="border-emerald-200 focus:border-emerald-500 dark:border-emerald-800"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  size="lg"
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <motion.span
                        className="w-2 h-2 rounded-full bg-white"
                        animate={{
                          scale: [1, 1.5, 1],
                          opacity: [0.5, 1, 0.5],
                        }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          ease: "easeInOut",
                        }}
                      />
                      <motion.span
                        className="w-2 h-2 rounded-full bg-white"
                        animate={{
                          scale: [1, 1.5, 1],
                          opacity: [0.5, 1, 0.5],
                        }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          ease: "easeInOut",
                          delay: 0.2,
                        }}
                      />
                      <motion.span
                        className="w-2 h-2 rounded-full bg-white"
                        animate={{
                          scale: [1, 1.5, 1],
                          opacity: [0.5, 1, 0.5],
                        }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          ease: "easeInOut",
                          delay: 0.4,
                        }}
                      />
                    </span>
                  ) : (
                    'Create Account'
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
                  Already have an account?{' '}
                  <Link
                    href="/signin"
                    className="text-emerald-600 dark:text-emerald-400 hover:underline font-medium"
                  >
                    Sign in
                  </Link>
                </p>
              </form>
            </CardContent>
          </Card>

          <div className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
            <p>
              By creating an account, you agree to our{' '}
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

