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
        Schema::create('alert_notifications', function (Blueprint $table) {
            $table->id();
            $table->string('external_event_id')->nullable()->unique();
            $table->string('type'); // zone_capacity, zone_full, criminal_detected, queue_stopped, queue_wait_time, etc.
            $table->string('severity'); // info, warning, critical, success
            $table->string('title');
            $table->text('message');
            $table->string('location')->nullable();
            $table->string('image_url')->nullable();
            $table->string('suspect_image_url')->nullable();
            $table->boolean('is_read')->default(false)->index();
            $table->timestamp('acknowledged_at')->nullable();
            $table->json('metadata')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('alert_notifications');
    }
};
