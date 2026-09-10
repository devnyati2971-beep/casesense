import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/status_chip.dart';

class DocumentsTab extends StatelessWidget {
  const DocumentsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(48),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Case Documents', style: Theme.of(context).textTheme.headlineMedium),
            PrimaryButton(label: 'Upload Document', icon: Icons.upload_file, onPressed: () {}),
          ],
        ),
        const SizedBox(height: 32),
        // Physical paper feel for documents
        _buildDocumentCard(context, 'FIR_Copy_Signed.pdf', 'PROCESSED', 4),
        _buildDocumentCard(context, 'Bail_Application_Draft_v1.docx', 'UPLOADED', 12),
        _buildDocumentCard(context, 'Witness_Statement_Scan.pdf', 'PROCESSING', 2),
      ],
    );
  }

  Widget _buildDocumentCard(BuildContext context, String name, String status, int pages) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.parchment,
        border: Border.all(color: AppColors.stone),
        borderRadius: BorderRadius.circular(4),
        boxShadow: [BoxShadow(color: AppColors.nearBlack.withValues(alpha: 0.05), blurRadius: 4, offset: const Offset(0, 2))],
      ),
      child: Row(
        children: [
          const Icon(Icons.picture_as_pdf, color: AppColors.subtleBronze, size: 32),
          const SizedBox(width: 24),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                Text('$pages pages • Added today', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.subtleBronze)),
              ],
            ),
          ),
          StatusChip(status: status),
          const SizedBox(width: 24),
          IconButton(icon: const Icon(Icons.more_vert, color: AppColors.charcoal), onPressed: () {}),
        ],
      ),
    );
  }
}