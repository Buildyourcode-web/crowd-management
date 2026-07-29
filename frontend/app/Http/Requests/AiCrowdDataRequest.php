<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;

class AiCrowdDataRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     */
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Get the validation rules that apply to the request.
     *
     * @return array<string, \Illuminate\Contracts\Validation\ValidationRule|array<mixed>|string>
     */
    public function rules(): array
    {
        return [
            'event_id' => 'nullable|string|max:100',
            'timestamp' => 'nullable|string',
            'summary' => 'required|array',
            'summary.total_entries' => 'required|integer|min:0',
            'summary.total_exits' => 'required|integer|min:0',
            'summary.total_visits' => 'nullable|integer|min:0',
            'zones' => 'required|array',
            'zones.*.id' => 'required|string',
            'zones.*.name' => 'required|string',
            'zones.*.current_count' => 'required|integer|min:0',
            'zones.*.capacity' => 'required|integer|min:1',
            'gates' => 'nullable|array',
            'gates.*.gate_number' => 'required|string',
            'gates.*.entries' => 'required|integer|min:0',
            'gates.*.exits' => 'required|integer|min:0',
            'gates.*.status' => 'required|string|in:normal,warning,blocked',
            'queues' => 'nullable|array',
            'queues.*.queue_number' => 'required|string',
            'queues.*.wait_minutes' => 'required|integer|min:0',
            'queues.*.movement' => 'required|string|in:moving,slow,stopped',
            'criminal_detection' => 'nullable|array',
            'criminal_detection.detected' => 'required_with:criminal_detection|boolean',
            'criminal_detection.detection_id' => 'required_if:criminal_detection.detected,true|string',
            'criminal_detection.person_reference' => 'nullable|string',
            'criminal_detection.confidence' => 'nullable|numeric|between:0,100',
            'criminal_detection.image_url' => 'nullable|string',
            'criminal_detection.suspect_image_url' => 'nullable|string',
            'criminal_detection.camera_name' => 'nullable|string',
            'criminal_detection.gate_name' => 'nullable|string',
            'criminal_detection.zone_name' => 'nullable|string',
            'criminal_detection.detected_at' => 'nullable|string',
            'hourly_trend' => 'nullable|array',
            'hourly_trend.*.time' => 'required|string',
            'hourly_trend.*.count' => 'required|integer|min:0',
        ];
    }

    /**
     * Handle a failed validation attempt and return clean JSON error messages.
     *
     * @param Validator $validator
     * @throws HttpResponseException
     */
    protected function failedValidation(Validator $validator)
    {
        throw new HttpResponseException(response()->json([
            'success' => false,
            'message' => 'Validation error.',
            'errors' => $validator->errors(),
        ], 422));
    }
}
