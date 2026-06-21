pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        APP_DIR = '/opt/gold-dashboard'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install & sanity check') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet -r requirements.txt
                    python -c "import app"   # import sanity check, fails the build fast
                '''
            }
        }

        stage('Deploy') {
            steps {
                // Jenkins user needs passwordless sudo for rsync/systemctl,
                // or swap this for an SSH-agent step if deploying to a remote box.
                sh 'chmod +x deploy/deploy.sh && ./deploy/deploy.sh'
            }
        }

        stage('Verify it stayed up') {
            steps {
                sh 'curl -sf http://localhost:5000/healthz'
            }
        }
    }

    post {
        success {
            echo 'Gold dashboard deployed and running under systemd (gold-dashboard.service).'
        }
        failure {
            echo 'Deploy failed — check the systemd service logs: journalctl -u gold-dashboard -n 100'
        }
    }
}
