#!/usr/bin/env python3
"""
Autonomous Sphero BOLT Race Script
Navigates a 5m x 3m course clockwise as fast as possible
Course consists of 50cm x 50cm panels
"""

import time
import math
import sys
from typing import Optional, List, Tuple
from spherov2 import scanner
from spherov2.types import Color
from spherov2.sphero_edu import SpheroEduAPI

class SpheroRacer:
    def __init__(self, toy_name: Optional[str] = None):
        self.toy = None
        self.api = None
        self.toy_name = toy_name
        self.start_time = None
        self.total_distance = 0.0
        self.calibrated = False
        
        # Course parameters (in cm)
        self.COURSE_WIDTH = 500  # 5m
        self.COURSE_HEIGHT = 300  # 3m
        self.PANEL_SIZE = 50     # 50cm x 50cm panels
        
        # Speed settings
        self.STRAIGHT_SPEED = 80   # High speed for straight segments
        self.TURN_SPEED = 40      # Slower speed for turns
        self.APPROACH_SPEED = 60  # Medium speed when approaching turns
          # Course waypoints (clockwise from start/finish line)
        # Coordinates in cm, heading in degrees
        # Aangepast voor het werkelijke parcours layout
        self.waypoints = [
            (200, 250, 0),        
            (450, 250, 0),      
            (450, 250, 90),     
            (450, 50, 90),   
            (450, 50, 180),     
            (350, 50, 180),      
            (350, 50, 270),     
            (350, 150, 270),     
            (350, 150, 180),       
            (150, 150, 180), 
            (150, 150, 90),   
            (150, 50, 90),   
            (150, 50, 180),   
            (50, 50, 180),   
            (50, 50, 270),   
            (50, 250, 270),   
            (50, 250, 0),   
            (250, 250, 0)   
        ]
        print("🤖 Sphero BOLT Autonomous Racer initialized")
        print(f"📏 Course: {self.COURSE_WIDTH}cm x {self.COURSE_HEIGHT}cm")

    def discover_nearest_toy(self):
        """Discover nearest Sphero toy"""
        try:
            toys = scanner.find_toys()
            if not toys:
                print("Geen Sphero's gevonden.")
                return None
            self.toy = toys[0]
            print(f"Dichtstbijzijnde Sphero toy '{self.toy.name}' ontdekt.")            
            return self.toy.name
        except Exception as e:
            print(f"Error no toys nearby: {e}")
            return None
    
    def discover_toy(self, toy_name):
        """Discover specific Sphero toy by name"""
        try:
            self.toy = scanner.find_toy(toy_name=toy_name)
            print(f"Sphero toy '{toy_name}' discovered.")
            return True
        except Exception as e:
            print(f"Error discovering toy: {e}")
            return False

    def connect_toy(self):
        """Connect to discovered Sphero toy"""
        if self.toy is not None:
            try:
                self.api = SpheroEduAPI(self.toy)
                # Initialize the robot
                self.api.reset_aim()
                self.api.set_main_led(Color(0, 0, 255))  # Blue LED - connected
                print("✅ Successfully connected to Sphero BOLT!")
                return True
            except Exception as e:
                print(f"Error connecting to toy: {e}")
                return False
        else:
            print("No toy discovered. Please run discover_toy() first.")
            return False

    def calibrate_heading(self) -> bool:
        """Manual calibration - set heading so 0° points to first segment"""
        try:
            print("\n🧭 CALIBRATION MODE")
            print("Position the Sphero behind the start/finish line")
            print("The robot should face the first straight segment (right)")
            print("Press ENTER when positioned correctly...")
            
            # Set calibration LED (red)
            self.api.set_main_led(Color(255, 0, 0))
            self.api.set_speed(0)
            
            # Wait for user confirmation
            input()
            
            # Reset heading to 0°
            self.api.reset_aim()
            self.api.set_heading(0)
            
            # Confirmation LED (green)
            self.api.set_main_led(Color(0, 255, 0))
            print("✅ Calibration complete! Robot heading set to 0°")
            
            time.sleep(1)
            self.calibrated = True
            return True
            
        except Exception as e:
            print(f"❌ Calibration failed: {e}")
            return False

    def calculate_distance(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float]) -> float:
        """Calculate distance between two points"""
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        return math.sqrt(dx*dx + dy*dy)

    def move_to_waypoint(self, x: float, y: float, heading: float, speed: int) -> bool:
        """Move to a specific waypoint"""
        try:
            print(f"🎯 Moving to ({x:.0f}, {y:.0f}) at heading {heading}° with speed {speed}")
            
            # Set heading and speed
            self.api.set_heading(heading)
            time.sleep(0.1)  # Small delay for heading adjustment
            self.api.set_speed(speed)
            return True
            
        except Exception as e:
            print(f"❌ Movement error: {e}")
            return False

    def execute_segment(self, start_waypoint: Tuple[float, float, float], 
                       end_waypoint: Tuple[float, float, float]) -> bool:
        """Execute movement between two waypoints"""
        try:
            start_x, start_y, start_heading = start_waypoint
            end_x, end_y, end_heading = end_waypoint
            
            # Calculate segment distance
            distance = self.calculate_distance((start_x, start_y), (end_x, end_y))
            
            if distance < 1:  # Turn in place (same coordinates, different heading)
                print(f"🔄 Turning in place to heading {end_heading}°")
                self.api.set_heading(end_heading)
                time.sleep(0.5)  # Time for turn to complete
                return True
            
            # Regular movement segment
            if abs(end_heading - start_heading) > 45:  # Turn segment
                speed = self.TURN_SPEED
                duration = distance / (speed * 0.6)  # Slower for turns
            else:  # Straight segment
                speed = self.STRAIGHT_SPEED
                duration = distance / (speed * 0.8)  # Estimate duration
            
            print(f"📏 Segment distance: {distance:.1f}cm, Duration: {duration:.1f}s")
            
            # Execute movement
            self.move_to_waypoint(end_x, end_y, end_heading, speed)
            
            # Wait for segment completion
            time.sleep(duration)
            
            self.total_distance += distance
            return True
            
        except Exception as e:
            print(f"❌ Segment execution failed: {e}")
            return False

    def run_race(self) -> bool:
        """Execute the complete race course"""
        try:
            if not self.calibrated:
                print("❌ Robot not calibrated! Run calibrate_heading() first.")
                return False
            
            print("\n🏁 Starting autonomous race!")
            print("Course: Clockwise navigation")
            
            # Set racing LED (purple)
            self.api.set_main_led(Color(255, 0, 255))
            
            # Start timer
            self.start_time = time.time()
            
            # Execute each segment
            for i in range(len(self.waypoints) - 1):
                segment_start = time.time()
                start_point = self.waypoints[i]
                end_point = self.waypoints[i + 1]
                
                print(f"\n📍 Segment {i+1}/{len(self.waypoints)-1}")
                
                if not self.execute_segment(start_point, end_point):
                    print(f"❌ Failed to execute segment {i+1}")
                    return False
                
                segment_time = time.time() - segment_start
                print(f"⏱️ Segment completed in {segment_time:.2f}s")
                
                # Brief pause between segments for stability
                time.sleep(0.2)
            
            # Stop at finish line
            self.api.set_speed(0)
            
            # Calculate race results
            race_time = time.time() - self.start_time
            avg_speed = self.total_distance / race_time if race_time > 0 else 0
            
            # Victory LED (gold)
            self.api.set_main_led(Color(255, 215, 0))
            
            print(f"\n🏆 RACE COMPLETE!")
            print(f"⏱️ Total time: {race_time:.2f} seconds")
            print(f"📏 Total distance: {self.total_distance:.1f} cm")
            print(f"🚀 Average speed: {avg_speed:.1f} cm/s")
            
            return True
            
        except Exception as e:
            print(f"❌ Race failed: {e}")
            self.emergency_stop()
            return False

    def emergency_stop(self):
        """Emergency stop function"""
        try:
            if self.api:
                self.api.set_speed(0)
                self.api.set_main_led(Color(255, 0, 0))  # Red LED for error
                print("🛑 EMERGENCY STOP ACTIVATED")
        except Exception as e:
            print(f"❌ Emergency stop failed: {e}")

    def cleanup(self):
        """Clean up resources"""
        try:
            if self.api:
                self.api.set_speed(0)
                self.api.set_main_led(Color(0, 0, 0))  # Turn off LED
                print("🧹 Cleanup complete")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

def main(toy_name, joystick=None, playerid=None):
    """Main execution function"""
    print("=" * 50)
    print("🤖 SPHERO BOLT AUTONOMOUS RACER")
    print("=" * 50)
    
    if toy_name is None:
        print("❌ No toy name provided")
        return False
        
    print(f"Try to connect to: {toy_name}")
    
    racer = SpheroRacer(toy_name=toy_name)
    
    try:        
        # Step 1: Discover Sphero
        if not racer.discover_toy(toy_name):
            print("❌ Failed to discover Sphero BOLT")
            return False
        
        # Step 1.5: Connect to Sphero
        if not racer.connect_toy():
            print("❌ Failed to connect to Sphero BOLT")
            return False
        
        # Step 2: Calibrate heading
        if not racer.calibrate_heading():
            print("❌ Failed to calibrate robot")
            return False
        
        # Step 3: Final preparation
        print("\n🏁 Ready to race!")
        print("Press ENTER to start the autonomous race...")
        input()
        
        # Step 4: Execute race
        success = racer.run_race()
        
        if success:
            print("\n✅ Autonomous race completed successfully!")
        else:
            print("\n❌ Race failed to complete")
            
        return success
        
    except KeyboardInterrupt:
        print("\n🛑 Race interrupted by user")
        racer.emergency_stop()
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        racer.emergency_stop()
        return False
        
    finally:
        racer.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python script.py <toy_name> <joystickNumber 0-1> <player 1-5>")
        sys.exit(1)
    
    toy_name = sys.argv[1]
    joystick = int(sys.argv[2])
    playerid = int(sys.argv[3])
    print(f"Try to connect to: {toy_name} with number {joystick} for player {playerid}")
    
    main(toy_name, joystick, playerid)