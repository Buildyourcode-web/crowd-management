<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('criminal_detections', function (Blueprint $table) {
            $table->id();
            $table->foreignId('criminal_record_id')->constrained('criminal_records')->onDelete('cascade');
            $table->string('camera_id');
            $table->string('zone_name');
            $table->string('captured_image');
            $table->integer('accuracy');
            $table->timestamp('captured_at');
            $table->string('status')->default('detected'); // detected, acknowledged
            $table->timestamp('acknowledged_at')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('criminal_detections');
    }
};
