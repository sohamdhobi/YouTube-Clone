from django.core.management.base import BaseCommand
from core.recommender import precompute_recommendations
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Precompute recommendations for active users to improve performance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            action='store_true',
            help='Run in a continuous loop with sleep interval'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,
            help='Sleep interval in seconds when running in loop mode (default: 1 hour)'
        )
    
    def handle(self, *args, **options):
        loop_mode = options['loop']
        interval = options['interval']
        
        if loop_mode:
            self.stdout.write(self.style.SUCCESS(f'Starting recommendation precomputation in loop mode with {interval}s interval'))
            try:
                while True:
                    self._run_precomputation()
                    self.stdout.write(f'Sleeping for {interval} seconds...')
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Received keyboard interrupt, stopping loop'))
        else:
            self.stdout.write(self.style.SUCCESS('Starting one-time recommendation precomputation'))
            self._run_precomputation()
    
    def _run_precomputation(self):
        """Run the precomputation function and log results"""
        start_time = time.time()
        try:
            result = precompute_recommendations()
            elapsed = time.time() - start_time
            
            if result:
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully precomputed recommendations in {elapsed:.2f} seconds'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'Precomputation completed with issues in {elapsed:.2f} seconds'
                ))
                
        except Exception as e:
            elapsed = time.time() - start_time
            self.stderr.write(self.style.ERROR(
                f'Error precomputing recommendations after {elapsed:.2f} seconds: {str(e)}'
            ))
            logger.exception('Error in precompute_recommendations command') 