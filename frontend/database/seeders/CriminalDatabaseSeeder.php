<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\CriminalRecord;
use App\Models\CriminalDetection;

class CriminalDatabaseSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        // 1. Seed 10 Criminal Records
        $criminals = [
            [
                'name' => 'John Doe',
                'criminal_code' => 'CRM-001',
                'profile_image' => '/storage/detections/suspect-mock-1.jpg',
                'description' => 'Wanted for grand theft auto. Known to frequent Zone A and Gate 01.',
                'status' => 'active'
            ],
            [
                'name' => 'Jane Smith',
                'criminal_code' => 'CRM-002',
                'profile_image' => '/storage/detections/suspect-mock-2.jpg',
                'description' => 'Suspect in financial fraud. Often identified near Gate 02 and Zone B.',
                'status' => 'active'
            ],
            [
                'name' => 'Robert Johnson',
                'criminal_code' => 'CRM-003',
                'profile_image' => '/storage/detections/suspect-mock-3.jpg',
                'description' => 'Wanted for shoplifting and trespassing in commercial zones.',
                'status' => 'active'
            ],
            [
                'name' => 'Michael Brown',
                'criminal_code' => 'CRM-004',
                'profile_image' => '/storage/detections/suspect-mock-4.jpg',
                'description' => 'Known pickpocket associate. Known locations: Gate 03, Zone C.',
                'status' => 'active'
            ],
            [
                'name' => 'Emily Davis',
                'criminal_code' => 'CRM-005',
                'profile_image' => '/storage/detections/suspect-mock-5.jpg',
                'description' => 'Wanted for vandalism and property damage.',
                'status' => 'active'
            ],
            [
                'name' => 'William Miller',
                'criminal_code' => 'CRM-006',
                'profile_image' => '/storage/detections/suspect-mock-6.jpg',
                'description' => 'Suspect in illegal street sales and trespassing.',
                'status' => 'active'
            ],
            [
                'name' => 'Olivia Garcia',
                'criminal_code' => 'CRM-007',
                'profile_image' => '/storage/detections/suspect-mock-7.jpg',
                'description' => 'Wanted for credit card fraud. Known to visit central plazas.',
                'status' => 'active'
            ],
            [
                'name' => 'David Martinez',
                'criminal_code' => 'CRM-008',
                'profile_image' => '/storage/detections/suspect-mock-8.jpg',
                'description' => 'Wanted for package theft in residential and security check zones.',
                'status' => 'active'
            ],
            [
                'name' => 'Sophia Rodriguez',
                'criminal_code' => 'CRM-009',
                'profile_image' => '/storage/detections/suspect-mock-9.jpg',
                'description' => 'Suspect in identification forgery and retail theft.',
                'status' => 'active'
            ],
            [
                'name' => 'James Wilson',
                'criminal_code' => 'CRM-010',
                'profile_image' => '/storage/detections/suspect-mock-10.jpg',
                'description' => 'Wanted for parole violation and public disturbance.',
                'status' => 'active'
            ]
        ];

        foreach ($criminals as $c) {
            CriminalRecord::create($c);
        }

        // 2. Seed 3 Active Detections referencing the first three criminals
        $detections = [
            [
                'criminal_record_id' => 1, // John Doe
                'camera_id' => 'CAM-04',
                'zone_name' => 'Zone A',
                'captured_image' => '/storage/detections/DET-mock-1.jpg',
                'accuracy' => 98,
                'captured_at' => now()->subMinutes(12),
                'status' => 'detected',
                'acknowledged_at' => null
            ],
            [
                'criminal_record_id' => 2, // Jane Smith
                'camera_id' => 'CAM-02',
                'zone_name' => 'Zone B',
                'captured_image' => '/storage/detections/DET-mock-2.jpg',
                'accuracy' => 95,
                'captured_at' => now()->subMinutes(8),
                'status' => 'detected',
                'acknowledged_at' => null
            ],
            [
                'criminal_record_id' => 3, // Robert Johnson
                'camera_id' => 'CAM-05',
                'zone_name' => 'Zone C',
                'captured_image' => '/storage/detections/DET-mock-3.jpg',
                'accuracy' => 92,
                'captured_at' => now()->subMinutes(3),
                'status' => 'detected',
                'acknowledged_at' => null
            ]
        ];

        foreach ($detections as $d) {
            CriminalDetection::create($d);
        }
    }
}
