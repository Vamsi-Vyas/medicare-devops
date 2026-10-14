
pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOY_VERSION',
            choices: ['blue', 'green'],
            description: 'Select the version to serve'
        )
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/Vamsi-Vyas/medicare-devops.git'
            }
        }

        stage('Validate Application') {
            steps {
                sh '''
                    set -eu
                    test -s app/index.html
                    grep -q "MediCare" app/index.html
                    echo "Application validation passed"
                '''
            }
        }

        stage('Security Scan - Application') {
            steps {
                sh '''
                    set -eu
                    trivy fs --scanners vuln,secret \
                        --severity HIGH,CRITICAL \
                        --exit-code 1 .
                '''
            }
        }

        stage('Security Scan - Dockerfile') {
            steps {
                sh '''
                    set -eu
                    trivy config --severity HIGH,CRITICAL \
                        --exit-code 1 Dockerfile
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t medicare-devops:${BUILD_NUMBER} .'
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    set -eu
                    NAME=medicare-test-${BUILD_NUMBER}
                    PORT=18081

                    docker rm -f "$NAME" >/dev/null 2>&1 || true

                    docker run -d --name "$NAME" \
                        -p 127.0.0.1:$PORT:8080 \
                        medicare-devops:${BUILD_NUMBER}

                    trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

                    for i in $(seq 1 20); do
                        if curl -fsS "http://127.0.0.1:$PORT/" \
                            | grep -q 'MediCare'; then
                            echo "Smoke test passed"
                            exit 0
                        fi
                        sleep 2
                    done

                    echo "Smoke test failed"
                    exit 1
                '''
            }
        }

        stage('Verify Kubernetes') {
            steps {
                sh '''
                    set -eu
                    export KUBECONFIG=/var/lib/jenkins/.kube/config

                    case "$DEPLOY_VERSION" in
                        blue|green) ;;
                        *)
                            echo "Invalid DEPLOY_VERSION: $DEPLOY_VERSION"
                            exit 1
                            ;;
                    esac

                    kubectl rollout status \
                        "deployment/medicare-${DEPLOY_VERSION}" \
                        --timeout=120s
                '''
            }
        }


stage('Switch Traffic') {
    steps {
        sh '''
            set -eu
            export KUBECONFIG=/var/lib/jenkins/.kube/config

            case "$DEPLOY_VERSION" in
              blue|green) ;;
              *) echo "Invalid deployment version"; exit 1 ;;
            esac

            PATCH="{\\"spec\\":{\\"selector\\":{\\"app\\":\\"medicare\\",\\"version\\":\\"${DEPLOY_VERSION}\\"}}}"

            echo "Switching traffic to ${DEPLOY_VERSION}"
            kubectl patch service medicare-service \
              --type=merge \
              -p "$PATCH"

            kubectl get service medicare-service \
              -o jsonpath='{.spec.selector}'
            echo
        '''
    }
}

        stage('Verify Served Version') {
            steps {
                sh '''
                    set -eu
                    export KUBECONFIG=/var/lib/jenkins/.kube/config

                    kubectl rollout status deployment/medicare-${DEPLOY_VERSION} \
                        --timeout=120s

                    kubectl port-forward service/medicare-service \
                        18082:80 >/tmp/medicare-port-forward.log 2>&1 &
                    PF_PID=$!
                    trap 'kill "$PF_PID" 2>/dev/null || true' EXIT

                    for i in $(seq 1 15); do
                        if curl -fsS http://127.0.0.1:18082/ \
                            -o /tmp/medicare-served.html; then
                            break
                        fi
                        sleep 2
                    done

                    grep -q "id=\\"version\\">${DEPLOY_VERSION^}<" \
                        /tmp/medicare-served.html

                    echo "Verified served version: ${DEPLOY_VERSION}"
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline and Blue-Green traffic switch succeeded'
        }

        failure {
            echo 'Pipeline failed. Review Console Output for the failed stage.'
        }
    }
}
